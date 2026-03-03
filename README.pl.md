# msgraph-token-refresh (PL)

Minimalna usluga do odswiezania tokenu aplikacyjnego Microsoft Graph (OAuth2 client credentials).
Token pobierany jest przez libcurl (pycurl), obsluguje proxy i jest zapisywany atomowo do pliku JSON.

## Funkcje

- Pobieranie tokenu przez `libcurl` (`pycurl`)
- Obsluga proxy (`PROXY_URL`, `PROXY_USERNAME`, `PROXY_PASSWORD`, `NO_PROXY`)
- Dynamiczny interwal odswiezania na podstawie `expires_in`
- Exponential backoff z jitterem przy bledach
- Atomowy zapis pliku tokenu z uprawnieniami `0600`
- Graceful shutdown (`SIGTERM`, `SIGINT`)

## Zmienne srodowiskowe

Wymagane:

- `TENANT_ID`
- `CLIENT_ID`

Opcjonalne:

- `GRAPH_URL` (domyslnie: `https://graph.microsoft.com`)
- `TOKEN_PATH` (domyslnie: `/tokens/.token.json`)
- `CLIENT_SECRET_FILE` (domyslnie: `/run/secrets/msgraph_client_secret`)
- `REFRESH_SAFETY_SECONDS` (domyslnie: `300`)
- `REFRESH_MIN_SECONDS` (domyslnie: `30`)
- `REFRESH_MAX_SECONDS` (domyslnie: `3300`)
- `ERROR_BACKOFF_INITIAL_SECONDS` (domyslnie: `5`)
- `ERROR_BACKOFF_MAX_SECONDS` (domyslnie: `300`)
- `CURL_CONNECT_TIMEOUT_SECONDS` (domyslnie: `10`)
- `CURL_TIMEOUT_SECONDS` (domyslnie: `30`)

Zmienne proxy:

- `PROXY_URL` (przyklad: `http://proxy.internal:3128`)
- `PROXY_USERNAME`
- `PROXY_PASSWORD`
- `NO_PROXY`

## Przyklad uruchomienia Docker

```bash
mkdir -p ./tokens
printf '%s' 'TWOJ_CLIENT_SECRET' > ./msgraph_client_secret

docker run --rm \
  -e TENANT_ID='00000000-0000-0000-0000-000000000000' \
  -e CLIENT_ID='00000000-0000-0000-0000-000000000000' \
  -e TOKEN_PATH='/tokens/.token.json' \
  -v "$(pwd)/tokens:/tokens" \
  -v "$(pwd)/msgraph_client_secret:/run/secrets/msgraph_client_secret:ro" \
  ghcr.io/mkilijanek/msgraph-token-refresh:latest
```

## Przyklad Docker Compose

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

## Format wyjsciowy

Przy sukcesie:

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

Przy bledzie:

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
