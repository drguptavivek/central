## VG fork customization docs

This repo includes VG-specific customizations for app user authentication and settings. For details, see:

- `docs/vg/vg_modsecurity.md` - Modsecurity WAF implementation
- `docs/vg/vg-core-central-edits.md` - Central meta-repo changes vs upstream
- `client/docs/vg_client_changes.md`
- `client/docs/vg_core_client_edits.md`
- `client/docs/vg-component-short-token-app-users.md`
- `server/docs/vg_api.md`
- `server/docs/vg_overview.md`
- `server/docs/vg_user_behavior.md`
- `server/docs/vg_settings.md`
- `server/docs/vg_implementation.md`
- `server/docs/vg_installation.md`
- `server/docs/vg_core_server_edits.md`
- `server/docs/vg_tests.md`

## SUBMODULES

This repo uses git submodules:

| Submodule | Path | Repository |
|-----------|------|------------|
| Backend | `server/` | `drguptavivek/central-backend.git` |
| Frontend | `client/` | `drguptavivek/central-frontend.git` |
| Knowledge Base | `agentic_kb/` | `drguptavivek/agentic_kb.git` |
| Nginx Base Image | `central-nginx-vg-base/` | `drguptavivek/central-nginx-vg-base.git` |
| OWASP CRS | `crs/` | `coreruleset/coreruleset.git` |

### Understanding Submodules

The main `central` repo only tracks **pointers** (SHA commits) to submodules, not the actual code. Changes inside `server/` or `client/` must be committed **inside** those directories first, then update the pointer in the parent `central` repo.

### Initial Setup

```bash
cd central

# Sync submodule config
git submodule sync --recursive

# Initialize and pull submodules
git submodule update --init --recursive

# Verify submodules
git submodule status
git config --get-regexp '^submodule\..*\.url$'
```

### Committing Submodule Changes

```bash
# Commit backend changes:
cd server && git status && git commit …
# Push to drguptavivek/central-backend on the current branch

# Then update the pointer in central:
cd .. && git add server && git commit …
# This updates the submodule SHA recorded in the parent repo
```

**Important:** Committing only in `central` without committing in `server`/`client` will not preserve the edits—they'll remain as "dirty submodule" changes.

## ENV

```bash
cd central && cp .env.template .env
```

Edit `.env` with:
```
DOMAIN=your-domain.com  # e.g., odk.epidemiology.tech
SYSADMIN_EMAIL=you@example.com
SSL_TYPE=upstream       # Use 'selfsign' only if not behind a proxy
```

If running locally without a real domain/proxy, add `127.0.0.1 central.local` to `/etc/hosts` and use `DOMAIN=central.local`.
```bash
sudo nano /etc/hosts
```

## DOCKER UP

### Current Docker Compose Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Pure upstream v2025.4.1 + Porst for PYXForm |
| `docker-compose.override.yml` | VG security configs (modsecurity) |
| `docker-compose.vg-dev.yml` | Profile management (same as upstream) + Client HMR overrides in nginx |

### Makefile Shortcuts

Use the `Makefile` targets to run the common dev/prod compose commands:

```bash
# Development (vg-dev profile)
make dev          # up -d
make dev-nond     # up (foreground)
make dev-build    # up -d --build
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql

make dev-logs     # logs --tail=50 -f
make stop         # stop (dev)

# Production (override only)
make prod         # up -d
make prod-nond    # up (foreground)
make prod-build   # up -d --build
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql

make prod-logs    # logs --tail=50 -f
make prod-stop    # stop (prod)
```

### Build and Start

```bash
cd central

# Build all services
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml build postgres14 enketo_redis_main enketo_redis_cache pyxform enketo mail secrets service

# Start services
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml up -d

# Install npm dependencies
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml run --rm service npm install

# Apply database migrations
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql

# Start service and nginx
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml up -d service nginx
```

**Backend is now running at:** congigured domain name

## USER CREATION

```bash
cd central

# Create user
docker compose --env-file .env exec service odk-cmd --email your@email.com user-create

# Promote to admin
docker compose exec service odk-cmd --email your@email.com user-promote
```

## BASH ACCESS

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec -it service bash
```

## LOGS

```bash
# Service logs
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml logs service -f --tail=50

# Modsecurity audit logs
tail -f logs/modsecurity/audit.log | jq
```

## TESTS

### Setup Test Database (one-time)

```bash
docker exec -e PGPASSWORD=odk central-postgres14-1 psql -U odk -c "CREATE ROLE odk_test_user LOGIN PASSWORD 'odk_test_pw'"
docker exec -e PGPASSWORD=odk central-postgres14-1 psql -U odk -c "CREATE DATABASE odk_integration_test OWNER odk_test_user"
docker exec -i central-postgres14-1 psql -U odk -d odk_integration_test < server/docs/sql/vg_app_user_auth.sql
```

### VG Password Unit Test

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/util/vg-password.js'
```

### VG Integration Tests

```bash
# App user auth tests
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha --recursive test/integration/api/vg-app-user-auth.js'

# Org app users tests
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-tests-orgAppUsers.js'

# Telemetry tests
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && node -v && NODE_CONFIG_ENV=test BCRYPT=insecure npx --prefix server mocha test/integration/api/vg-telemetry.js'

# Enketo status tests
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && node -v && NODE_CONFIG_ENV=test BCRYPT=insecure npx --prefix server mocha test/integration/api/vg-enketo-status.js'
```

### Standard ODK Integration Tests

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api'

# With different reporters
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api --reporter dot'

docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api --reporter min'
```

## STOP CONTAINERS

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml down
```
