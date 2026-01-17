# VG Fork: Short-Lived Token App Users

> **Last Updated**: 2026-01-02

This document provides a detailed overview of the VG “short-lived token app users” work: what changed, why, how it works end-to-end, and where the authoritative server/client documentation lives.

## Overview

Upstream ODK Central app users (field keys) rely on a long-lived token that can be shared via QR code. 
VG replaces that model with:

- Username/password login for app users
- Short-lived bearer tokens (configurable TTL)
- Session caps (configurable)
- Stronger operational controls (password reset/change, revoke/deactivate/reactivate, audit trails)
- Optional managed QR code support (no embedded credentials)

## Goals and non-goals

### Goals

- Prevent long-lived app-user credentials from being embedded into a QR code.
- Make app-user access revocable immediately (revoke/terminate sessions).
- Make app-user credentials rotatable (reset/change password) without requiring token rotation workflows.
- Provide observability and operational control (audit logs, session listing, throttling/lockouts, telemetry).

### Non-goals

- App users logging into the Central web UI (still not supported).
- Cookie-based auth for app users (bearer-only).
- A public API for all VG settings (some are DB-only today).

## End-to-end flow (happy path)

1. Admin creates an app user in the project (VG UI) with username + phone; the UI generates an initial password and shows it to the admin.
2. App user logs in with `POST /v1/projects/:projectId/app-users/login` to get a short-lived bearer token (and `expiresAt`).
3. App user uses the token for subsequent API calls via `Authorization: Bearer <token>` (no cookies).
4. When the token expires, the app usdocker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml up -d

### 3. Apply DB migrations
```bash
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql
```

### 4. Install dependencies
```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml run --rm service npm installssword hash, phone, active flag).
- `vg_settings`: global VG key/value settings (TTL/cap, lockout settings, `admin_pw`, and optional web-user lockout duration).
- `vg_project_settings`: per-project overrides for selected keys (TTL/cap/admin_pw, and app-user lockout settings).
- `vg_app_user_sessions`: per-token metadata (ip/user-agent/deviceId/comments) and expiry tracking.
- `vg_app_user_login_attempts` + `vg_app_user_lockouts`: throttle/lockout tracking for app-user login.
- `vg_app_user_telemetry`: app-user device telemetry (see telemetry docs/tests).

## Settings model (high level)

- Global defaults live in `vg_settings` and are seeded by the migration (TTL defaults to `3` days, cap defaults to `3`).
- Project overrides (where supported) live in `vg_project_settings`.
- `admin_pw` is used in managed QR payloads for ODK Collect settings lock (and has project overrides).
- Web-user login hardening for `/v1/sessions` optionally reads `vg_web_user_lock_duration_minutes` from `vg_settings` (fallback to `10` if missing/invalid).

See: `docs/vg/vg-server/vg_settings.md`.

## Server: API surface (summary)

### App user authentication and lifecycle

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/projects/:projectId/app-users/login` | App-user login; returns short-lived bearer token + `expiresAt`. |
| `POST` | `/v1/projects/:projectId/app-users/:id/password/change` | App user changes their own password (requires current auth). |
| `POST` | `/v1/projects/:projectId/app-users/:id/password/reset` | Admin resets an app user password. |
| `POST` | `/v1/projects/:projectId/app-users/:id/revoke` | App user revokes their own current session. |
| `POST` | `/v1/projects/:projectId/app-users/:id/revoke-admin` | Admin deactivates an app user (revokes sessions). |
| `POST` | `/v1/projects/:projectId/app-users/:id/active` | Admin activates/deactivates app user. |
| `GET` | `/v1/projects/:projectId/app-users/:id/sessions` | Admin lists app-user sessions/metadata. |

### Settings endpoints (system + project)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/system/settings` | Read system defaults for TTL/cap/`admin_pw`. |
| `PUT` | `/v1/system/settings` | Update system defaults for TTL/cap/`admin_pw`. |
| `GET` | `/v1/projects/:projectId/app-users/settings` | Read project-effective TTL/cap/`admin_pw` (includes overrides). |
| `PUT` | `/v1/projects/:projectId/app-users/settings` | Update project overrides for TTL/cap/`admin_pw`. |
| `POST` | `/v1/system/app-users/lockouts/clear` | Admin clears app-user lockouts (does not change config values). |

### Telemetry

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/projects/:projectId/app-users/telemetry` | App user submits device telemetry. |
| `GET` | `/v1/system/app-users/telemetry` | System admin lists telemetry with filters/paging. |

See: `docs/vg/vg-server/vg_api.md` and `docs/vg/vg-server/vg_implementation.md`.

## Client: UX surface (summary)

VG modifies the Central web UI to support the new app-user lifecycle:

- App user list shows username + phone, and supports edit/reset/revoke/restore workflows.
- App user views can show active sessions/devices to help admins spot concurrent usage.
- Create + reset flows generate a password and present it to the admin (credentials are not embedded into the QR).
- System-level settings UI for TTL/cap/`admin_pw`.
- Project-level app-user settings UI for TTL/cap/`admin_pw` overrides.

See: `docs/vg/vg-client/vg_client_changes.md`.

## Security model (high level)

- Tokens are short-lived and bearer-only; app-user requests use `Authorization: Bearer <token>`.
- Session expiry is fixed at issuance (no sliding refresh).
- Session caps revoke older sessions on login when exceeded.
- App-user login enforces username+IP lockouts with project-overridable lockout settings.
- Admins can deactivate/reactivate users and clear lockouts; actions are audited.
- QR codes are for configuration (server URL/project), not for embedding credentials; managed QR payload includes `admin_pw` for Collect settings lock (not user credentials).

## Collect UX notes (VG)

- Collect shows token validity and can notify the user to revalidate before expiry.
- Revalidation is achieved via app-user login (password) and PIN gating on app relaunch.

## Where to read next

### Server (backend)

- `docs/vg/vg-server/vg_overview.md`
- `docs/vg/vg-server/vg_api.md`
- `docs/vg/vg-server/vg_security.md`
- `docs/vg/vg-server/vg_core_server_edits.md`
- `docs/vg/vg-server/vg_settings.md`
- `docs/vg/vg-server/vg_user_behavior.md`
- `docs/vg/vg-server/vg_implementation.md`
- `docs/vg/vg-server/vg_installation.md`
- `docs/vg/vg-server/vg_tests.md`
- `docs/vg/vg-server/vg_web_login_hardening.md`

### Client (frontend)

- `docs/vg/vg-client/vg_client_changes.md`
- `docs/vg/vg-client/vg_core_client_edits.md`

### Cross-cutting

- `docs/vg/qr-code-generation.md`
- `docs/vg/qr-code-all-possible-managed-settings.md`


## Tests (where to look)

VG coverage spans integration + unit tests (see `docs/vg/vg-server/vg_tests.md` for the current inventory/counts and commands):

- `server/test/integration/api/vg-app-user-auth.js`
- `server/test/integration/api/vg-tests-orgAppUsers.js`
- `server/test/integration/api/vg-telemetry.js`
- `server/test/integration/api/vg-webusers.js`
- `server/test/unit/util/vg-password.js`
- `server/test/unit/domain/vg-app-user-auth.js`
