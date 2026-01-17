# VG App User Auth - Implementation

> **Last Updated**: 2026-01-02

This document lists the key implementation points and modified core behavior.

## Tables

- `vg_field_key_auth`: One-to-one with `field_keys` by `actorId`. Stores username, password hash, phone, and active flag.
- `vg_settings`: Stores global settings (session TTL/cap, app-user lockout config, `admin_pw`, and optional web-user lockout duration).
- `vg_project_settings`: Stores project-level overrides for session TTL/cap and lockout settings.
- `vg_app_user_login_attempts`: Stores login attempts for lockout enforcement.
- `vg_app_user_lockouts`: Stores active lockout windows.
- `vg_app_user_sessions`: Stores IP/device metadata (user agent, deviceId, comments) per active session (token FK to `sessions`).
- `vg_app_user_telemetry`: Stores app-user device telemetry (deviceId, Collect version, device timestamps, location).

## Core modules

- `server/lib/domain/vg-app-user-auth.js`: Orchestrates login, password change/reset, revoke, and activate/deactivate; emits vg audit events.
- `server/lib/domain/vg-telemetry.js`: Validates and records app-user telemetry payloads.
- `server/lib/model/query/vg-app-user-auth.js`: Data access for VG auth, settings lookup, and login attempt tracking.
- `server/lib/model/query/vg-telemetry.js`: Data access for telemetry insert and filtered listing.
- `server/lib/resources/vg-app-user-auth.js`: Exposes system + project app-user settings endpoints for TTL/cap/`admin_pw`, and admin lockout clear endpoint.
- `server/lib/resources/vg-telemetry.js`: Exposes app-user telemetry capture and admin listing endpoints.
- `server/lib/resources/sessions.js`: Implements web-user login hardening (lockouts, audit, response headers); reads `vg_web_user_lock_duration_minutes` from `vg_settings`.

## File-by-file details

- `server/lib/domain/vg-app-user-auth.js`
  - `createAppUser()`: validates username/password/phone/name, creates field key without session, inserts `vg_field_key_auth`, emits audit.
  - `updateAppUser()`: updates display name and phone, emits audit.
  - `login()`: enforces lockout, verifies password, issues session with TTL, trims by cap, emits audit.
  - `changePassword()`: verifies old password, enforces policy, rotates sessions, emits audit.
  - `resetPassword()`: admin reset, enforces policy, rotates sessions, emits audit.
  - `revokeSessions()`: terminates sessions for actor (optionally current token), emits audit.
  - `setActive()`: toggles active flag, terminates sessions on deactivate, emits audit.
- `server/lib/model/query/vg-app-user-auth.js`
  - `getSessionTtlDays()` / `getSessionCap()`: read defaults (3 days, cap 3).
  - `getSettingWithProjectOverride()`: prefers project-level overrides when issuing sessions.
  - `insertAuth()`, `updatePassword()`, `updatePhone()`, `setActive()`: CRUD for `vg_field_key_auth`.
  - `recordAttempt()` / `getLockStatus()`: login attempt tracking and lockout checks.
  - `recordSession()` / `getActiveSessionsByActorId()`: session metadata tracking and listing.
- `server/lib/domain/vg-telemetry.js`
  - `recordTelemetry()`: validates telemetry payload and inserts record for the authenticated app user.
- `server/lib/model/query/vg-telemetry.js`
  - `insertTelemetry()`: writes telemetry fields to `vg_app_user_telemetry`.
  - `getTelemetry()`: lists telemetry with filters (projectId, deviceId, appUserId, dateFrom/dateTo) and pagination.
- `server/lib/resources/vg-app-user-auth.js`
  - Maps HTTP routes to the domain functions and enforces auth/permission checks.
- `server/lib/resources/vg-telemetry.js`
  - `POST /projects/:projectId/app-users/telemetry`: app-user telemetry capture.
  - `GET /system/app-users/telemetry`: system-admin telemetry listing with filters and pagination.
- `server/lib/model/query/sessions.js`
  - Rejects sessions for deactivated app users (`vg_active=false`).
- `server/lib/model/query/field-keys.js`
  - Joins `vg_field_key_auth` so app-user responses include username/phone/active.

## Endpoint to handler mapping

- `POST /projects/:projectId/app-users/login` -> `vgAppUserAuth.login()`
- `POST /projects/:projectId/app-users/:id/password/change` -> `vgAppUserAuth.changePassword()`
- `POST /projects/:projectId/app-users/:id/password/reset` -> `vgAppUserAuth.resetPassword()`
- `POST /projects/:projectId/app-users/:id/revoke` -> `vgAppUserAuth.revokeSessions()` (self)
- `POST /projects/:projectId/app-users/:id/revoke-admin` -> `vgAppUserAuth.setActive(false)`
- `GET /projects/:projectId/app-users/:id/sessions` -> `vgAppUserAuth.listSessions()`
- `POST /projects/:projectId/app-users/:id/active` -> `vgAppUserAuth.setActive(active)`
- `GET /projects/:projectId/app-users/settings` -> `VgAppUserAuth.getSettingWithProjectOverride*()`
- `PUT /projects/:projectId/app-users/settings` -> `VgAppUserAuth.upsertProjectSetting()`
- `POST /system/app-users/lockouts/clear` -> `vgAppUserAuth.clearLockout()`
- `POST /projects/:projectId/app-users/telemetry` -> `vgTelemetry.recordTelemetry()`
- `GET /system/app-users/telemetry` -> `VgTelemetry.getTelemetry()`
- `GET /system/settings` -> `VgAppUserAuth.getSessionTtlDays()` + `getSessionCap()` + `getAdminPw()`
- `PUT /system/settings` -> `VgAppUserAuth.upsertSetting()`

## Modified upstream behavior

- `server/lib/model/query/sessions.js`: Enforces `vg_active` for app-user sessions.
- `server/lib/model/query/field-keys.js`: Joins `vg_field_key_auth` data into app-user responses.

## Session handling

- Session TTL is loaded from `vg_settings` with optional project override (`vg_app_user_session_ttl_days`) when issuing tokens.
- No sliding refresh is applied; expiry is fixed at issuance.

## Audit events

VG emits vg-prefixed actions for creation, login success/failure, password change/reset, session revocation, and activation/deactivation.

## Migrations

- `server/docs/sql/vg_app_user_auth.sql`: Creates VG tables (including telemetry) and seeds defaults (TTL 3, cap 3).

## Rate limiting and lockouts

- Login attempts are recorded in `vg_app_user_login_attempts` for username+IP lockouts.
- Lockouts are stored in `vg_app_user_lockouts` with project overrides in `vg_project_settings`.
- Session TTL and cap also support project overrides via `vg_project_settings`.
- Lockouts are enforced in `server/lib/domain/vg-app-user-auth.js` using `getActiveLockout()` and `getLockStatus()` from `server/lib/model/query/vg-app-user-auth.js`.
- Web-user login lockouts for `/v1/sessions` are implemented in `server/lib/resources/sessions.js` and use a fixed threshold/window with a configurable duration from `vg_settings` (`vg_web_user_lock_duration_minutes`).

## Operational command (Docker)

Apply the schema migration in a local Docker setup:

```bash
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql


# TESTS
# - The test suite runs core migrations (server/lib/model/migrations) on the test DB in server/   test/integration/setup.js.
 # - Then it runs fixtures, including server/test/integration/fixtures/03-vg-app-user-auth.js,  which creates the VG tables (vg_field_key_auth, vg_settings, vg_app_user_login_attempts,    vg_app_user_sessions, vg_app_user_telemetry) for the test DB.
#  So the test DB is populated via fixtures, not server/docs/sql/vg_app_user_auth.sql. That SQL file is for manual setup/upgrade outside the test harness.

docker exec -i central-postgres14-1 psql -U odk -c "DROP DATABASE IF EXISTS odk_integration_test;"
docker exec -i central-postgres14-1 psql -U odk -c "CREATE DATABASE odk_integration_test;"
docker exec -i central-postgres14-1 psql -U odk -d odk_integration_test -c "CREATE SCHEMA IF  NOT EXISTS public; ALTER SCHEMA public OWNER TO odk; GRANT USAGE, CREATE ON SCHEMA public TO odk_test_user;"
docker exec -i central-postgres14-1 psql -U odk -c "ALTER ROLE odk_test_user SET search_path =public;"
docker exec -i central-postgres14-1 psql -U odk -c "ALTER DATABASE odk_integration_test SET  search_path = public;"

docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'PGPASSWORD=odk_test_pw psql -h postgres14 -U  odk_test_user -d odk_integration_test -c "SHOW search_path;"'

docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_ENV=test NODE_CONFIG_ENV=test   BCRYPT=insecure npx mocha --recursive test/integration/api/vg-app-user-auth.js'

docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_ENV=test NODE_CONFIG_ENV=test   BCRYPT=insecure npx mocha --recursive test/integration/api/vg-telemetry.js'

```
