# VG App User Auth - Security Controls

> **Last Updated**: 2026-01-02

This document consolidates VG security controls implemented in the Central backend/client fork, and clarifies which controls are configurable via UI/API vs DB-only.

## App user authentication model

- App users authenticate using username/password and receive a **short-lived bearer token** on login.
- Tokens are bearer-only (no cookies) and have a fixed expiry (no sliding refresh).
- App users are **project-scoped**.

## Password policy (server enforced)

- Minimum 10 characters
- Maximum 72 characters
- Requires at least one: uppercase, lowercase, digit, special (`~!@#$%^&*()_+-=,.`)
- Enforced on create, change, and reset password operations.

## Session expiry and concurrent session control

Controls:

- **Session TTL**: server enforces token expiry based on `vg_app_user_session_ttl_days`.
- **Session cap**: server enforces a maximum number of active sessions based on `vg_app_user_session_cap`.
  - When the cap is exceeded, older sessions are revoked (trimmed) after login.

Configuration:

- UI/API:
  - System defaults: `GET/PUT /v1/system/settings` (`vg_app_user_session_ttl_days`, `vg_app_user_session_cap`, `admin_pw`)
  - Project overrides: `GET/PUT /v1/projects/:projectId/app-users/settings` (`vg_app_user_session_ttl_days`, `vg_app_user_session_cap`, `admin_pw`)
- DB:
  - `vg_settings` for global values
  - `vg_project_settings` for per-project overrides

## App-user login throttling and lockouts (server-side brute-force protection)

Controls:

- Failed app-user logins are tracked in `vg_app_user_login_attempts`.
- Lockouts are enforced via `vg_app_user_lockouts`.
- Lockout decision is based on **username + IP** and a configurable window:
  - `vg_app_user_lock_max_failures`
  - `vg_app_user_lock_window_minutes`
  - `vg_app_user_lock_duration_minutes`

Defaults (seeded by migration):

- 5 failures within 5 minutes → lock for 10 minutes

Configuration:

- UI/API: not currently exposed.
- DB-only:
  - Global defaults in `vg_settings`
  - Optional per-project overrides in `vg_project_settings`

Operational control:

- Admins can clear app-user lockouts via `POST /v1/system/app-users/lockouts/clear` (optionally scoped by IP).

## Web-user login hardening (`/v1/sessions`)

Controls (non-OIDC):

- Failed login audits with normalized identifiers.
- Lockout behavior after repeated failures.
- Response headers such as attempts remaining and Retry-After on lockout.
- Timing normalization behavior to reduce account enumeration signals.

Configuration:

- `vg_web_user_lock_duration_minutes` (optional) is read from `vg_settings` if present and a positive integer; otherwise the server falls back to `10`.
- UI/API: not currently exposed (DB-only in `vg_settings`).

See: `vg_web_login_hardening.md`

## Activation, revocation, and credential rotation

Controls:

- Deactivate/revoke blocks authentication and terminates sessions.
- Reactivate restores ability to authenticate.
- Password change/reset terminates existing sessions (forces re-login).

Configuration:

- These are workflow controls, not numeric settings.

## Auditing

Controls:

- VG emits `vg.*` audit actions for major lifecycle events (create/update, login success/failure, password change/reset, session revoke, activate/deactivate, lockout clear).
- Web-user login hardening also logs upstream `user.session.*` actions for web login flows.

## Managed QR and `admin_pw`

Controls:

- QR codes are used for configuration and do not embed app-user credentials.
- Managed QR payloads include `admin_pw` for ODK Collect settings lock.

Security exception / rationale:

- `admin_pw` is intentionally stored and served as plain text because it must be included in the managed QR payload for ODK Collect settings lock.
- This means `admin_pw` should be treated as a **shared secret** (not a per-user credential) and is expected to be exposed to anyone who can view/scan the managed QR.
- Use this control to prevent casual settings changes in Collect, not as a high-security authentication factor.

Configuration:

- UI/API exposed via system and project settings endpoints (see Session expiry and concurrent session control section).

## Sources of truth

- Settings and validation: `docs/vg/vg-server/vg_settings.md`
- API routes: `docs/vg/vg-server/vg_api.md` and `docs/vg/vg-server/routes/`
- Tests: `docs/vg/vg-server/vg_tests.md`
