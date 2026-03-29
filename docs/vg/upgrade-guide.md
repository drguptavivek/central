---
title: VG Central — Upgrade Guide
type: howto
domain: ODK-Central-vg
tags:
  - upgrade
  - docker
  - deployment
  - migration
status: approved
created: 2026-03-29
updated: 2026-03-29
---

# VG Central — Upgrade Guide

How to upgrade a running VG Central Docker installation to a new VG release.

## Before you start

Load your `.env` into the shell so the commands below use the correct values:

```bash
set -a && source .env && set +a
```

Check the [changelog](changelog-v2025.4.4.md) for the target version (breaking changes, new settings).

Take a Postgres backup:

```bash
docker compose exec postgres14 pg_dump -U "${DB_USER:-odk}" "${DB_NAME:-odk}" \
  | gzip > odk-backup-$(date +%Y%m%d).sql.gz
```

Note your current version:

```bash
curl -sk "https://${DOMAIN}/version.txt"
```

## Upgrade steps

### 1. Pull the new release

```bash
git fetch origin --tags
git checkout v2025.4.4-vg.1        # or the target tag
git submodule update --init --recursive
```

### 2. Rebuild images

```bash
make prod-build
```

This rebuilds `service` and `nginx` with the new code and restarts the stack.

### 3. DB migrations run automatically

The `service` container runs all pending Knex migrations (upstream + VG) on startup. No manual SQL required.

To verify after startup:

```bash
# Check migration table for the latest VG migration
docker compose exec postgres14 psql -U "${DB_USER:-odk}" "${DB_NAME:-odk}" \
  -c "SELECT name FROM knex_migrations ORDER BY id DESC LIMIT 5;"

# Confirm VG tables exist
docker compose exec postgres14 psql -U "${DB_USER:-odk}" "${DB_NAME:-odk}" \
  -c "\dt vg_*"
```

### 4. Verify

```bash
make prod-logs                            # watch for errors
curl -sk "https://${DOMAIN}/version.txt"
```

Browse to the Central UI and confirm login works.

## Upgrading from a pre-March 2026 install (manual SQL era)

If you previously applied `server/docs/sql/vg_app_user_auth.sql` manually, the VG migration
is idempotent (`CREATE TABLE IF NOT EXISTS`) — the server will skip tables that already exist
and apply only the new additions (if any). No action needed on your part.

## Rolling back

If you need to roll back:

```bash
git checkout <previous-tag>
git submodule update --init --recursive
make prod-build
```

Postgres down-migrations are provided (`.down.sql`) for upstream migrations but are rarely
needed. If a VG migration must be reversed, apply the corresponding `.down.sql` manually:

```bash
docker compose exec -T postgres14 psql -U "${DB_USER:-odk}" "${DB_NAME:-odk}" \
  < server/lib/model/migrations/20260307-01-vg-app-user-auth-base.down.sql
```

## VG-specific settings after upgrade

New VG settings introduced in a release are seeded with defaults by the migration.
To review current settings:

```bash
docker compose exec postgres14 psql -U "${DB_USER:-odk}" "${DB_NAME:-odk}" \
  -c "SELECT vg_key_name, vg_key_value FROM vg_settings ORDER BY vg_key_name;"
```

To update a setting via the API:

```bash
curl -s -X PUT "https://${DOMAIN}/v1/system/settings" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"vg_app_user_session_ttl_days": 7}'
```

## See also

- [quick-install.md](quick-install.md) — fresh install
- [AGENTS.md](../../AGENTS.md) — upstream upgrade workflow (for maintainers)
- Changelogs: [v2025.4.4](changelog-v2025.4.4.md) | [v2025.4.3](changelog-v2025.4.3.md)
