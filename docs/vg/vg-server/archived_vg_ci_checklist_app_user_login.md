# Archived: CI checklist for vg app-user login + short tokens

This document is archived. Ongoing guidance now lives in:

- `server/docs/vg_overview.md`
- `server/docs/vg_implementation.md`
- `server/docs/vg_tests.md`

Purpose: track implementation steps for the vg_* app-user login, password policy, and short-lived session work so it remains mergeable against upstream.

## Migration and schema
- [x] Apply SQL migration at docs/sql/vg_app_user_auth.sql (creates vg_field_key_auth, vg_settings seeded with vg_app_user_session_ttl_days=3, vg_app_user_login_attempts).

## Model/query layer
- [x] Add vg_field_key_auth frame/query (actorId FK/PK) and helpers (create with password, set password, set active, get by vg_username).
- [x] Add vg_app_user_auth query helpers for lockout checks and recording attempts using vg_app_user_login_attempts.
- [x] Ensure Sessions.create/bearer lookup rejects vg_active=false and uses TTL from vg_settings (vg_app_user_session_ttl_days=3 default).

## Domain/helpers
- [x] Implement vg_app_user_password policy helper (10 chars, upper/lower/digit/special).
- [x] Implement vg_app_user_auth orchestration (login, change/reset password, revoke, deactivate) using vg_field_key_auth and vg_settings TTL.
- [x] Define vg_* audit action identifiers and emit events (create, login success/failure, password change/reset, sessions revoke, activate/deactivate).

## HTTP/resources
- [x] Wire new vg app-user auth routes (login, change, reset, self revoke, admin revoke, deactivate/reactivate).
- [x] Adjust app-user create/update to require vg_username/password and populate vg_field_key_auth alongside field_keys.
- [x] Login routes remain bearer-only (no cookies) to minimize CSRF; add CSRF tokens only if cookies introduced later.

## Rate limiting and lockout
- [x] Enforce 5 failed attempts in 5 minutes -> 10-minute lockout, keyed by vg_username+IP.
- [x] Persist attempts to vg_app_user_login_attempts; audit login failures.

## Testing
- [x] Integration tests for create/login/lockout/change/reset/revoke/deactivate, session TTL/cap, audit logging.
- [x] Unit tests for password policy.

## Deployment/configuration
- [x] Document new config key vg_app_user_session_ttl_days and defaults.
- [x] Document new config key vg_app_user_session_cap (default 3) and seed in vg_settings.
- [ ] Document schema changes and rollout order (migrate before deploy). Reference docs/sql/vg_app_user_auth.sql for the migration.

## Post-deploy verification
- [ ] Verify new app-user creation, login, and token issuance with 3-day expiry.
- [ ] Verify lockout behavior and reset path.
- [ ] Verify deactivate blocks auth and revokes sessions.
