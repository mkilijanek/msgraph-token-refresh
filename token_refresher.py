import json
import os
import time
from datetime import datetime, timezone

import msal


def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise SystemExit(f"Missing env var: {name}")
    return v


def read_secret_from_docker_secret(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


TENANT_ID = env("TENANT_ID")
CLIENT_ID = env("CLIENT_ID")
GRAPH_URL = env("GRAPH_URL", "https://graph.microsoft.com")
TOKEN_PATH = env("TOKEN_PATH", "/tokens/.token.json")
REFRESH_SECONDS = int(env("REFRESH_SECONDS", "3300"))

# docker secrets default mount: /run/secrets/<name>
CLIENT_SECRET = read_secret_from_docker_secret("/run/secrets/msgraph_client_secret")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = [f"{GRAPH_URL}/.default"]  # application permissions

app = msal.ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY,
)

os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)


def write_token(payload: dict) -> None:
    tmp_path = TOKEN_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, TOKEN_PATH)


while True:
    result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" not in result:
        # minimalny log błędu
        err = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "error": result.get("error"),
            "error_description": result.get("error_description"),
            "correlation_id": result.get("correlation_id"),
        }
        write_token({"ok": False, **err})
        time.sleep(60)
        continue

    # MSAL zwraca expires_in (sekundy)
    now = int(time.time())
    expires_in = int(result.get("expires_in", 3600))
    expires_at = now + expires_in

    token_doc = {
        "ok": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "token_type": result.get("token_type", "Bearer"),
        "access_token": result["access_token"],
        "expires_in": expires_in,
        "expires_at": expires_at,
        "scope": result.get("scope"),
    }
    write_token(token_doc)

    time.sleep(REFRESH_SECONDS)
