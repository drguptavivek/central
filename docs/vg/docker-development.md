# Docker development (VG)

> **Last Updated**: 2026-01-02

This repo uses `docker compose` with layered config files for local development.

## Files

- `docker-compose.yml`: base services and defaults
- `docker-compose.override.yml`: local dev overrides (bind mounts, `client-dev`, etc.)
- `docker-compose.dev.yml`: `--profile central` dev wiring (ports, dev secrets, `SKIP_FRONTEND_BUILD` for nginx build)

## Start the dev stack (backend + nginx + postgres + enketo)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central up -d
```

## Run the frontend dev server (Vite/HMR)

`nginx` proxies `/` to the Vite server at `http://client-dev:8989`.

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central up -d client-dev
```

If `nginx` logs `host not found in upstream "client-dev"`, `client-dev` is not running or not on the same compose network; start it with the command above.

## Rebuild (service/nginx)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central build service nginx
```

Note: the nginx image build supports `SKIP_FRONTEND_BUILD=1` (wired via `docker-compose.dev.yml`) to avoid building the frontend during the nginx image build.

## Logs

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central logs -f --tail=100 service nginx client-dev
```

## Reset / clean

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central down
docker volume ls | rg 'central' || true
```
