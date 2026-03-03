# msgraph-token-refresh (EN)

A minimal service that refreshes Microsoft Graph app-only access tokens using OAuth2 client credentials flow.
The token is fetched via libcurl (pycurl), supports proxy configuration, and is written atomically to a JSON file.

## Features

- Token fetch via `libcurl` (`pycurl`)
- Proxy support (`PROXY_URL`, `PROXY_USERNAME`, `PROXY_PASSWORD`, `NO_PROXY`)
- Dynamic refresh interval based on `expires_in`
- Exponential backoff with jitter on errors
- Atomic token write with file mode `0600`
- Graceful shutdown (`SIGTERM`, `SIGINT`)

## Environment variables

Required:

- `TENANT_ID`
- `CLIENT_ID`

Optional:

- `GRAPH_URL` (default: `https://graph.microsoft.com`)
- `TOKEN_PATH` (default: `/tokens/.token.json`)
- `CLIENT_SECRET_FILE` (default: `/run/secrets/msgraph_client_secret`)
- `REFRESH_SAFETY_SECONDS` (default: `300`)
- `REFRESH_MIN_SECONDS` (default: `30`)
- `REFRESH_MAX_SECONDS` (default: `3300`)
- `ERROR_BACKOFF_INITIAL_SECONDS` (default: `5`)
- `ERROR_BACKOFF_MAX_SECONDS` (default: `300`)
- `CURL_CONNECT_TIMEOUT_SECONDS` (default: `10`)
- `CURL_TIMEOUT_SECONDS` (default: `30`)

Proxy variables:

- `PROXY_URL` (example: `http://proxy.internal:3128`)
- `PROXY_USERNAME`
- `PROXY_PASSWORD`
- `NO_PROXY`

## Docker run example

```bash
mkdir -p ./tokens
printf '%s' 'YOUR_CLIENT_SECRET' > ./msgraph_client_secret

docker run --rm \
  -e TENANT_ID='00000000-0000-0000-0000-000000000000' \
  -e CLIENT_ID='00000000-0000-0000-0000-000000000000' \
  -e TOKEN_PATH='/tokens/.token.json' \
  -v "$(pwd)/tokens:/tokens" \
  -v "$(pwd)/msgraph_client_secret:/run/secrets/msgraph_client_secret:ro" \
  ghcr.io/mkilijanek/msgraph-token-refresh:latest
```

## Docker Compose example

```yaml
services:
  token-refresher:
    image: ghcr.io/mkilijanek/msgraph-token-refresh:latest
    restart: unless-stopped
    environment:
      TENANT_ID: "00000000-0000-0000-0000-000000000000"
      CLIENT_ID: "00000000-0000-0000-0000-000000000000"
      TOKEN_PATH: "/tokens/.token.json"
    volumes:
      - ./tokens:/tokens
      - ./msgraph_client_secret:/run/secrets/msgraph_client_secret:ro
```

## Output format

Success payload:

```json
{
  "ok": true,
  "ts": "2026-03-03T12:00:00+00:00",
  "token_type": "Bearer",
  "access_token": "...",
  "expires_in": 3600,
  "expires_at": 1760000000,
  "scope": "https://graph.microsoft.com/.default"
}
```

Error payload:

```json
{
  "ok": false,
  "ts": "2026-03-03T12:00:00+00:00",
  "error": "network_error",
  "error_description": "Failed to connect",
  "http_status": 0,
  "curl_errno": 7
}
```
