# Docker development (VG)

> **Last Updated**: 2026-03-08

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

## Start on VM boot

The dev stack includes restart policies for long-running containers, including the Vite `client` container. To also create/start the Compose project after a VM reboot, install the tracked systemd unit:

```bash
make dev-autostart-install
make dev-autostart-status
```

The unit runs `make dev` from `/home/ndus/central` after Docker and the network are available.


## Access the application

- **Frontend**: https://central.local
- **Backend API**: https://central.local/v1/...
- **Enketo**: proxied through nginx

## Rebuild (service/nginx)

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml build service nginx
```

To rebuild the Dockerized frontend dev image as well:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml build client
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
- **Client Container**: Runs `start-dev.sh`, installs npm dependencies at startup, creates `.nginx` temp paths, then starts nginx + Vite on internal port `8989`.
- **HMR**: Upgraded via Nginx to WSS on port 443.
- **Service Container**: Runs `files/service/scripts/start-odk-dev.sh`, which renders config, runs migrations, then starts the backend under `node --watch`.
- **Nginx Container**: Uses `start-with-logrotate.sh` so nginx and modsecurity logs rotate inside the container during long-running dev sessions.

### How to Run
The `client` service starts automatically with the dev stack:

### Access
- Open your browser to your configured domain (e.g., `https://odk.epidemiology.tech` or `https://localhost:8443`).
- **Do NOT** access port 8989 directly (it is internal only).
- You should see the App. Changes to `client/src` will be reflected instantly (HMR).

### Client Dev Container Notes

- `client/Dockerfile.dev` includes Chromium so Karma tests can run inside the container.
- `client/start-dev.sh` must exist in the bind-mounted client worktree; if it is missing on the checked-out branch, container startup will fail because the bind mount hides the copy baked into the image.
- `.nginx` runtime temp directories are created at startup to avoid nginx permission/path failures on a clean branch.

## Ports

| Service | Internal Port | External Port (dev) |
|---------|---------------|---------------------|
| nginx | 80/443 | 80/443 |
| postgres14 | 5432 | 5432 |
| pyxform | 80 | 5001 |
| enketo | 8005 | 8005 |
| enketo_redis_main | 6379 | 63799 |
| enketo_redis_cache | 6379 | 63800 |

## Troubleshooting

### `/version.txt` returns 404 in dev
In the dev stack, nginx proxies `location /` to the Vite client (`client:8989`), so `/version.txt` is served by Vite rather than nginx static files. If your external proxy points at the dev stack, `/version.txt` may 404. Use the prod stack for `/version.txt`, or add a dev nginx override to serve it directly.

### Service reports missing migration files
If `service` reports that the migration directory is corrupt or references missing
VG migration files from an older branch, reset the local dev database/volumes and
start again from the clean branch state. In this migration, that issue was caused
by stale local DB state from an older feature branch.

### Client tests fail inside Docker
The client test path in Docker currently depends on:

- Chromium in `client/Dockerfile.dev`
- Karma using a container-safe launcher
- `test/run.sh` generating a simple `public/index.html` for the Karma/Webpack path

Even with those fixes, the broader client suite still has unresolved application
test failures/timeouts.

## Dev Secrets

Development uses hardcoded insecure secrets (defined in `docker-compose.vg-dev.yml`):
- `enketo-secret`: `s0m3v3rys3cr3tk3y`
- `enketo-less-secret`: `this $3cr3t key is crackable`
- `enketo-api-key`: `enketorules`

**WARNING**: Never use these secrets in production!
