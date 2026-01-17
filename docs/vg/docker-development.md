# Docker development (VG)

> **Last Updated**: 2026-01-14

This repo uses `docker compose` with layered config files for local development.

## Files

- `docker-compose.yml`: base services and defaults (pure upstream)
- `docker-compose.override.yml`: VG security configs (modsecurity, CRS only)
- `docker-compose.vg-dev.yml`: Development overrides (ports, dev secrets, HMR client) - **modified**

## Pure Upstream Files

The following files match upstream ODK Central exactly:
- `docker-compose.yml` ✅

Verification:
```bash
git diff upstream/master -- docker-compose.yml
# Should produce no output
```

## Quick Start (Makefile)

Use the Makefile shortcuts for common dev operations:

```bash
make dev   # Start the full dev stack (build + detach)
make stop  # Stop the dev stack
```

## Start the dev stack (manual)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml up -d
```

## Access the application

- **Frontend**: https://central.local
- **Backend API**: https://central.local/v1/...
- **Enketo**: proxied through nginx

## Rebuild (service/nginx)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml build service nginx
```

## Logs

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml logs -f --tail=100 service nginx
```

## Reset / clean

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml down
docker volume ls | rg 'central' || true
```

## Frontend Development (Dev-Prod Parity)

We use a "Dev-Prod Parity" architecture where Nginx proxies to a Dockerized client container, instead of serving static files. This supports Hot Module Replacement (HMR) while maintaining exact production routing (SSL, Domain, Headers).

### Architecture
- **Nginx**: Mounts `files/nginx/odk.conf.dev.template` which proxies `/` to `http://client:8989`.
- **Client Container**: Runs Vite in dev mode (internal port 8989).
- **HMR**: Upgraded via Nginx to WSS on port 443.

### How to Run
The `client` service starts automatically with the dev stack:

### Access
- Open your browser to your configured domain (e.g., `https://odk.epidemiology.tech` or `https://localhost:8443`).
- **Do NOT** access port 8989 directly (it is internal only).
- You should see the App. Changes to `client/src` will be reflected instantly (HMR).

## Ports

| Service | Internal Port | External Port (dev) |
|---------|---------------|---------------------|
| nginx | 80/443 | 80/443 |
| postgres14 | 5432 | 5432 |
| pyxform | 80 | 5001 |
| enketo | 8005 | 8005 |
| enketo_redis_main | 6379 | 63799 |
| enketo_redis_cache | 6379 | 63800 |

## Dev Secrets

Development uses hardcoded insecure secrets (defined in `docker-compose.vg-dev.yml`):
- `enketo-secret`: `s0m3v3rys3cr3tk3y`
- `enketo-less-secret`: `this $3cr3t key is crackable`
- `enketo-api-key`: `enketorules`

**WARNING**: Never use these secrets in production!
