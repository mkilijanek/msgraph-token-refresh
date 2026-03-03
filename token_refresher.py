import io
import json
import os
import random
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import pycurl


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise SystemExit(f"Missing env var: {name}")
    return value


def env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value in (None, ""):
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"Invalid int env var: {name}={raw_value!r}") from exc


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_secret(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        value = file.read().strip()
    if value == "":
        raise SystemExit(f"Secret file is empty: {path}")
    return value


def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


TENANT_ID = env("TENANT_ID")
CLIENT_ID = env("CLIENT_ID")
GRAPH_URL = env("GRAPH_URL", "https://graph.microsoft.com")
TOKEN_PATH = env("TOKEN_PATH", "/tokens/.token.json")
CLIENT_SECRET_FILE = env("CLIENT_SECRET_FILE", "/run/secrets/msgraph_client_secret")
CLIENT_SECRET = read_secret(CLIENT_SECRET_FILE)

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
TOKEN_ENDPOINT = f"{AUTHORITY}/oauth2/v2.0/token"
SCOPE = f"{GRAPH_URL}/.default"

PROXY_URL = os.getenv("PROXY_URL", "")
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")
NO_PROXY = os.getenv("NO_PROXY", "")
CURL_CONNECT_TIMEOUT_SECONDS = env_int("CURL_CONNECT_TIMEOUT_SECONDS", 10)
CURL_TIMEOUT_SECONDS = env_int("CURL_TIMEOUT_SECONDS", 30)

REFRESH_SAFETY_SECONDS = env_int("REFRESH_SAFETY_SECONDS", 300)
REFRESH_MIN_SECONDS = env_int("REFRESH_MIN_SECONDS", 30)
REFRESH_MAX_SECONDS = env_int("REFRESH_MAX_SECONDS", 3300)
ERROR_BACKOFF_INITIAL_SECONDS = env_int("ERROR_BACKOFF_INITIAL_SECONDS", 5)
ERROR_BACKOFF_MAX_SECONDS = env_int("ERROR_BACKOFF_MAX_SECONDS", 300)

if REFRESH_MIN_SECONDS > REFRESH_MAX_SECONDS:
    raise SystemExit("REFRESH_MIN_SECONDS must be <= REFRESH_MAX_SECONDS")

token_path = Path(TOKEN_PATH)
token_path.parent.mkdir(parents=True, exist_ok=True)

stop_requested = False


def _handle_stop_signal(signum: int, _frame: object) -> None:
    global stop_requested
    stop_requested = True
    print(json.dumps({"ts": now_iso(), "event": "shutdown_signal", "signal": signum}), flush=True)


signal.signal(signal.SIGTERM, _handle_stop_signal)
signal.signal(signal.SIGINT, _handle_stop_signal)


def write_token(payload: dict) -> None:
    tmp_path = str(token_path) + ".tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    os.replace(tmp_path, token_path)
    os.chmod(token_path, 0o600)


def _curl_error_payload(error: pycurl.error) -> dict:
    err_no, err_text = error.args
    return {
        "error": "network_error",
        "error_description": err_text,
        "curl_errno": err_no,
    }


def acquire_token_with_libcurl() -> dict:
    post_body = urlencode(
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": SCOPE,
            "grant_type": "client_credentials",
        }
    )
    response_buffer = io.BytesIO()
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, TOKEN_ENDPOINT)
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.POSTFIELDS, post_body)
    curl.setopt(pycurl.HTTPHEADER, ["Content-Type: application/x-www-form-urlencoded"])
    curl.setopt(pycurl.CONNECTTIMEOUT, CURL_CONNECT_TIMEOUT_SECONDS)
    curl.setopt(pycurl.TIMEOUT, CURL_TIMEOUT_SECONDS)
    curl.setopt(pycurl.WRITEDATA, response_buffer)
    curl.setopt(pycurl.SSL_VERIFYPEER, 1)
    curl.setopt(pycurl.SSL_VERIFYHOST, 2)

    if PROXY_URL:
        curl.setopt(pycurl.PROXY, PROXY_URL)
    if PROXY_USERNAME:
        curl.setopt(pycurl.PROXYUSERNAME, PROXY_USERNAME)
    if PROXY_PASSWORD:
        curl.setopt(pycurl.PROXYPASSWORD, PROXY_PASSWORD)
    if NO_PROXY:
        curl.setopt(pycurl.NOPROXY, NO_PROXY)

    try:
        curl.perform()
    except pycurl.error as error:
        return _curl_error_payload(error)
    finally:
        http_status = curl.getinfo(pycurl.RESPONSE_CODE)
        curl.close()

    raw_body = response_buffer.getvalue().decode("utf-8", errors="replace")
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return {
            "error": "invalid_response",
            "error_description": f"Token endpoint returned non-JSON body (HTTP {http_status})",
            "http_status": http_status,
            "response_snippet": raw_body[:300],
        }

    if http_status >= 400:
        return {
            "error": body.get("error", "http_error"),
            "error_description": body.get("error_description", f"HTTP {http_status}"),
            "correlation_id": body.get("correlation_id"),
            "http_status": http_status,
        }

    return body


def sleep_or_stop(seconds: int) -> bool:
    deadline = time.time() + max(0, seconds)
    while not stop_requested:
        remaining = int(deadline - time.time())
        if remaining <= 0:
            return True
        time.sleep(min(1, remaining))
    return False


def main() -> None:
    error_backoff = ERROR_BACKOFF_INITIAL_SECONDS

    while not stop_requested:
        result = acquire_token_with_libcurl()

        if "access_token" not in result:
            error_doc = {
                "ok": False,
                "ts": now_iso(),
                "error": result.get("error"),
                "error_description": result.get("error_description"),
                "correlation_id": result.get("correlation_id"),
                "http_status": result.get("http_status"),
                "curl_errno": result.get("curl_errno"),
            }
            write_token(error_doc)

            jitter = random.uniform(0, max(1.0, error_backoff * 0.2))
            sleep_seconds = min(ERROR_BACKOFF_MAX_SECONDS, int(error_backoff + jitter))
            print(
                json.dumps(
                    {
                        "ts": now_iso(),
                        "event": "token_refresh_error",
                        "sleep_seconds": sleep_seconds,
                        "error": error_doc["error"],
                    }
                ),
                flush=True,
            )

            if not sleep_or_stop(sleep_seconds):
                break
            error_backoff = min(ERROR_BACKOFF_MAX_SECONDS, error_backoff * 2)
            continue

        error_backoff = ERROR_BACKOFF_INITIAL_SECONDS

        now = int(time.time())
        expires_in = int(result.get("expires_in", 3600))
        expires_at = now + expires_in
        next_sleep = clamp(expires_in - REFRESH_SAFETY_SECONDS, REFRESH_MIN_SECONDS, REFRESH_MAX_SECONDS)

        token_doc = {
            "ok": True,
            "ts": now_iso(),
            "token_type": result.get("token_type", "Bearer"),
            "access_token": result["access_token"],
            "expires_in": expires_in,
            "expires_at": expires_at,
            "scope": result.get("scope"),
        }
        write_token(token_doc)
        print(
            json.dumps(
                {
                    "ts": now_iso(),
                    "event": "token_refreshed",
                    "expires_in": expires_in,
                    "next_refresh_in": next_sleep,
                }
            ),
            flush=True,
        )

        if not sleep_or_stop(next_sleep):
            break

    print(json.dumps({"ts": now_iso(), "event": "exit"}), flush=True)


if __name__ == "__main__":
    main()
