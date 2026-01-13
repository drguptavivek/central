# Docker development (VG)

> **Last Updated**: 2026-01-14

This repo uses `docker compose` with layered config files for local development.

## Files

- `docker-compose.yml`: base services and defaults (pure upstream)
- `docker-compose.override.yml`: VG security configs (modsecurity, CRS only)
- `docker-compose.dev.yml`: `--profile central` dev wiring (ports, dev secrets) - **pure upstream**

## Pure Upstream Files

The following files match upstream ODK Central exactly:
- `docker-compose.yml` ✅
- `docker-compose.dev.yml` ✅

Verification:
```bash
git diff upstream/master -- docker-compose.yml docker-compose.dev.yml
# Should produce no output
```

## Start the dev stack (backend + nginx + postgres + enketo)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central up -d
```

## Access the application

- **Frontend**: https://central.local
- **Backend API**: https://central.local/v1/...
- **Enketo**: proxied through nginx

## Rebuild (service/nginx)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central build service nginx
```

## Logs

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central logs -f --tail=100 service nginx
```

## Reset / clean

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central down
docker volume ls | rg 'central' || true
```

## Frontend Development

For frontend HMR development, you need to set up the client dev environment separately. See the client submodule documentation for details:

```bash
cd client
npm run dev  # Starts Vite dev server on port 8989
```

The client's Vite dev server proxies API calls to `https://central.local` through nginx.

## Ports

| Service | Internal Port | External Port (dev) |
|---------|---------------|---------------------|
| nginx | 80/443 | 80/443 |
| postgres14 | 5432 | 5432 |
| pyxform | 80 | 5001 |
| enketo | 8005 | 8005 |
| enketo_redis_main | 6379 | 6379 |
| enketo_redis_cache | 6379 | 6380 |

## Dev Secrets

Development uses hardcoded insecure secrets (defined in `docker-compose.dev.yml`):
- `enketo-secret`: `s0m3v3rys3cr3tk3y`
- `enketo-less-secret`: `this $3cr3t key is crackable`
- `enketo-api-key`: `enketorules`

**WARNING**: Never use these secrets in production!
