# VG App User Auth - Installation

This document lists the steps to set up VG-specific server changes for app-user auth.

## Prerequisites

- Central backend set up per the upstream instructions.
- Database access for applying the VG schema migration.
- For Docker-based dev, the `central-postgres14-1` container must be running.

## Step 1: Apply VG schema migration

Run the VG SQL migration to create the new tables/columns and seed defaults:

```sh
docker exec -i central-postgres14-1 psql -U odk -d odk < docs/sql/vg_app_user_auth.sql
```

If you're upgrading an existing VG install, re-run the same SQL to add new columns
(`device_id`, `comments`), the telemetry table, and the `vg_settings` constraint.

This creates:

- `vg_field_key_auth`
- `vg_settings` (seeds TTL 3 days, cap 3)
- `vg_app_user_login_attempts`
- `vg_app_user_lockouts`
- `vg_app_user_sessions`
- `vg_app_user_telemetry`

## Step 2: Verify settings (optional)

Check the seeded settings:

```sh
docker exec -i central-postgres14-1 psql -U odk -d odk -c "select vg_key_name, vg_key_value from vg_settings where vg_key_name in ('vg_app_user_session_ttl_days','vg_app_user_session_cap');"
```

Defaults are `3` and `3` respectively.

## Step 2a: Verify tables and counts (optional)

```sh
docker exec -i central-postgres14-1 psql -U odk -d odk -c "\\dt vg_*"
```

```sh
docker exec -i central-postgres14-1 psql -U odk -d odk -c "select count(*) from vg_field_key_auth;"
```

```sh
docker exec -i central-postgres14-1 psql -U odk -d odk -c "select count(*) from vg_app_user_login_attempts;"
```

```sh
docker exec -i central-postgres14-1 psql -U odk -d odk -c "select count(*) from vg_app_user_telemetry;"
```

## Step 3: Start the server

Run the backend using the usual `make run` (or Docker compose flow for the full stack).

## Step 4: Create an admin user

Create and promote a Central admin (required for app-user management):

```sh
docker compose --env-file .env exec service odk-cmd --email you@example.com user-create
```

```sh
docker compose exec service odk-cmd --email you@example.com user-promote
```

## Step 5: Admin configuration (optional)

Admins can update the session settings via the system settings endpoint:

- `GET /system/settings`
- `PUT /system/settings`

Requires `config.read` and `config.set` permissions, respectively.

## Step 6: Create a project

Create a project in the Central web UI (app users are project-scoped).

## Step 7: Create an app user

Using the Central web UI (Project > App Users), create an app user with:

- `username`
- display name (full name)
- optional phone

Password is auto-generated on create. Use the admin reset endpoint if you need to set a specific password.

## Step 8: Verify VG app-user auth

- Create an app user (admin/manager) with `username` and `password`.
- Log in via `POST /projects/:projectId/app-users/login` to get a short-lived token.
- Confirm token expiry and session cap behavior.

## Step 9: Run VG tests (optional)

After the server is running, you can run the VG-focused tests:

```sh
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha --recursive test/integration/api/vg-app-user-auth.js'
```

```sh
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-tests-orgAppUsers.js'
```

```sh
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/util/vg-password.js'
```

```sh
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-telemetry.js'
```

## Notes

- App users do not log in to the Central web UI.
- Tokens are bearer-only and expire based on TTL.
- Older sessions are revoked on login when the cap is exceeded.
- Login lockouts are stored in `vg_app_user_login_attempts`. To clear a lockout for a user+IP:
  ```sh
  docker exec -i central-postgres14-1 psql -U odk -d odk -c "delete from vg_app_user_login_attempts where username='vguser' and ip='1.2.3.4' and succeeded=false;"
  ```
- Admin alternative: `POST /system/app-users/lockouts/clear` with `{ "username": "...", "ip": "..." }`.
- Session listing: `GET /projects/:projectId/app-users/:id/sessions` to view IP/user-agent/deviceId/comments metadata for active sessions.
