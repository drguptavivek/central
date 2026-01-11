# ODK Central VG Fork - Development Getting Started

This guide is for **local development** (backend + frontend) using the layered compose files and `client-dev`.

For production/self-hosting, see `docs/vg/GETTING-STARTED-PRODUCTION.md`.

---

## Prereqs

- Docker + Docker Compose plugin
- Git
- Submodules initialized (`client/` + `server/`)

---

## Step 1: Clone and Initialize Submodules

```bash
# From repo root
git submodule sync --recursive
git submodule update --init --recursive
git submodule status
```

---

## Step 2: Configure `.env`

### Option A (recommended): generate

```bash
./scripts/init-odk.sh
```

Notes:
- Every run creates `.env.backup.YYYYMMDD-HHMMSS`.
- If you select Garage, it also generates `docker-compose-garage.yml`, `garage/garage.toml`, `garage/storage.conf` and writes `*.backup.YYYYMMDD-HHMMSS` before overwriting any of them.

For local dev, choose:
- Environment: `Dev`
- SSL: `selfsign`
- S3: `None` (simplest)
- Database: `Container`

### Option B: manual

```bash
cp .env.template .env
```

Minimum for local dev:
```bash
DOMAIN=central.local
SYSADMIN_EMAIL=you@example.com
SSL_TYPE=selfsign
```

---

## Step 3: /etc/hosts (or local DNS)

```bash
sudo sh -lc 'printf \"\\n127.0.0.1 central.local\\n\" >> /etc/hosts'
```

If you use Garage later, you’ll also need:
```text
127.0.0.1 odk-central.s3.central.local web.central.local
```

---

## Step 4: Build + Start (Dev Profile)

**Note**: The `init-odk.sh` script (Step 2) automatically created `docker-compose.dev-override.yml` and `docker-compose.dev.yml` from their `.example` templates when you selected "Dev" environment. These files are gitignored to prevent dev config from interfering with production deployments.

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev-override.yml \
  -f docker-compose.dev.yml \
  --profile central \
  build

docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev-override.yml \
  -f docker-compose.dev.yml \
  --profile central \
  up -d
```

---

## Step 5: Database Setup (VG)

```bash
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql
```

---

## Step 6: Admin User

```bash
docker compose exec service odk-cmd --email your@email.com user-create
docker compose exec service odk-cmd --email your@email.com user-promote
docker compose exec service odk-cmd --email your@email.com user-set-password
```

---

## Step 7: Frontend Dev (HMR via https://central.local)

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev-override.yml \
  -f docker-compose.dev.yml \
  --profile central \
  up -d client-dev
```

Then open `https://central.local` (accept the self-signed cert).

---

## VG Docs

- Deployment docs index: `docs/vg/README.md`
- VG client docs: `docs/vg/vg-client/`
- VG server docs: `docs/vg/vg-server/`
