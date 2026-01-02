# VG App User Auth - Overview

> **Last Updated**: 2026-01-02

## Scope

This fork introduces short-lived, password-based authentication for app users (field keys). It replaces long-lived token QR credentials with login-issued bearer tokens and adds server-side session controls.

App-user auth changes are the primary focus; This fork also hardens web user login behavior for `/v1/sessions` (see related docs).

## Key changes (behavior)

- App users authenticate with username/password to obtain short-lived bearer tokens.
- Tokens are bearer-only (no cookies) and expire based on TTL (default 3 days).
- Active sessions per app user are capped (default 3); oldest sessions are revoked on login when cap is exceeded.
- App users cannot log in to the Central web UI; they only use app-user endpoints.
- App user records now include username and phone; username is normalized to lowercase.
- Deactivation immediately revokes sessions and blocks further authentication.
- Login attempts are rate-limited (5 failures in 5 minutes per username+IP => 10-minute lock).
- Legacy long-lived field-key sessions without a matching `vg_field_key_auth` row are rejected.
- Session metadata (IP/user agent/deviceId/comments) is captured for admin viewing.
- App-user telemetry is captured (deviceId, Collect version, device timestamps, location) and is available to system admins via a paginated listing.
- Web user login hardening: failed login audits, lockouts, and timing normalization.

## Defaults

- `vg_app_user_session_ttl_days`: 3
- `vg_app_user_session_cap`: 3

## Related docs

- User behavior: [vg_user_behavior.md](vg_user_behavior.md)
- Security controls: [vg_security.md](vg_security.md)
- Settings: [vg_settings.md](vg_settings.md)
- API: [vg_api.md](vg_api.md)
- Implementation: [vg_implementation.md](vg_implementation.md)
- Installation: [vg_installation.md](vg_installation.md)
- Tests: [vg_tests.md](vg_tests.md)
- Core edits: [vg_core_server_edits.md](vg_core_server_edits.md)
- Web login hardening: [vg_web_login_hardening.md](vg_web_login_hardening.md)
