# ODK Central VG Fork - Production Getting Started

This is the **production/self-hosting** quickstart. It assumes you will run ODK Central behind an **upstream reverse proxy** (recommended).

For development workflows, see `docs/vg/GETTING-STARTED.md`.

---

## What You Will Run

- ODK Central (docker compose) listens on:
  - `HTTP_PORT=8080` (nginx inside the stack)
  - `HTTPS_PORT=8443` (unused in upstream mode)
- Your upstream proxy (Nginx/Caddy/Traefik) terminates TLS on `:443` and proxies to `http://<host>:8080`.

---

## Step 0: Prereqs

- A real domain (example: `central.example.com`) pointing to your server IP.
- Docker + Docker Compose plugin.
- An upstream proxy with TLS certificates (Let’s Encrypt or corporate CA).

If you plan to use **Garage S3**, you also need DNS for:
- `odk-central.s3.<DOMAIN>`
- `web.<DOMAIN>`

---

## Step 1: Generate Config

From repo root:

```bash
./scripts/init-odk.sh
```

Recommended selections for the “simple production” path:
- **Environment**: `Prod`
- **SSL**: `upstream`
- **S3**: `None` (default) or `Garage` (optional)
- **Database**: `Container`

Notes:
- Every run creates a timestamped backup like `.env.backup.YYYYMMDD-HHMMSS`.
- If you select Garage, `docker-compose-garage.yml`, `garage/garage.toml`, and `garage/storage.conf` are generated (and gitignored). If any already exist and would change, a timestamped `*.backup.YYYYMMDD-HHMMSS` is created first.

---

## Step 2: Create Docker Networks (Once)

```bash
docker network create central_db_net || true
docker network create central_web || true
```

---

## Step 3: Build

```bash
docker compose build
```

---

## Step 4: Start

### Option A (Default): No S3 (blobs in PostgreSQL)

```bash
docker compose up -d
```

### Option B (Optional): Garage S3

```bash
# Start Garage only
docker compose -f docker-compose.yml -f docker-compose-garage.yml up -d garage

# Bootstrap Garage (layout/key/bucket) and write S3 creds to .env
./scripts/add-s3.sh

# Start the full stack with the Garage overlay
docker compose -f docker-compose.yml -f docker-compose-garage.yml up -d
```

---

## Step 5: Configure Upstream Reverse Proxy

Your proxy must:
- preserve `Host`
- set `X-Forwarded-Proto: https`
- proxy to `http://127.0.0.1:8080` (or your Docker host IP)

### Example: Nginx

```nginx
server {
  listen 443 ssl;
  server_name central.example.com;

  # ssl_certificate ...
  # ssl_certificate_key ...

  location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

If using **Garage S3**, add additional `server` blocks for:
- `odk-central.s3.central.example.com`
- `web.central.example.com`

All should proxy to the same upstream (`:8080`) and preserve `Host`.

---

## Step 6: Verify

```bash
docker compose ps
docker compose logs -f --tail=100 nginx service
```

From your workstation:

```bash
curl -I https://<DOMAIN>/
curl -I https://<DOMAIN>/v1/
```

If using Garage:

```bash
curl -I https://odk-central.s3.<DOMAIN>/
curl -I https://web.<DOMAIN>/
```

---

## Troubleshooting (Fast)

- Check logs: `docker compose logs -f --tail=200 nginx service`
- Upstream proxy issues: confirm it sets `X-Forwarded-Proto https` and forwards `Host`
- Garage bootstrap: re-run `./scripts/add-s3.sh` (safe to re-run)
