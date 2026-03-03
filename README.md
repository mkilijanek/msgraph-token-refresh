# msgraph-token-refresh

Minimal service that refreshes Microsoft Graph app-only access tokens and writes them to a JSON file.

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

Proxy (libcurl):

- `PROXY_URL` (example: `http://proxy.internal:3128`)
- `PROXY_USERNAME`
- `PROXY_PASSWORD`
- `NO_PROXY`

## Output format

On success:

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

On error:

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
