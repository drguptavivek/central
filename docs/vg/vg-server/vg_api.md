# VG API Documentation

> **Last Updated**: 2026-02-08

VG customizations to ODK Central authentication and security:
- **App User Auth**: Short-lived, password-based bearer tokens for Collect users (project-scoped)
- **Web User Auth**: TOTP 2FA two-phase login with session cookies (system-wide)

## App User Auth
Short-lived, password-based auth for Collect-style app users tied to projects. Tokens are bearer-only (no cookies) and expire based on `vg_app_user_session_ttl_days` (default 3 days) stored in `vg_settings`, with optional per-project overrides.

## Web User TOTP 2FA
Two-phase login for web users with TOTP (Time-based One-Time Password) 2FA enabled:
- **Phase 1**: Email + Password → Returns temporary 60s token (no cookies)
- **Phase 2**: TOTP code with Bearer auth → Sets session cookies, extends expiration
- See [routes/web-user-totp.md](routes/web-user-totp.md) for API contracts

## Related docs

- Overview: [vg_overview.md](vg_overview.md)
- Security controls: [vg_security.md](vg_security.md)
- Settings: [vg_settings.md](vg_settings.md)
- User behavior: [vg_user_behavior.md](vg_user_behavior.md)
- Implementation: [vg_implementation.md](vg_implementation.md)
- Tests: [vg_tests.md](vg_tests.md)

## Frontend quick reference
- No long-lived tokens are ever returned from create/list endpoints; only `/login` returns a short-lived bearer token.
- Listings always include `token: null`; use `/login` to obtain a token for data submission.
- Session cap and TTL are enforced server-side; per-project overrides are supported via `vg_project_settings`.
- All app-user requests must include `Authorization: Bearer <short-token>` (never cookies).
- Common error codes: `400` validation, `401` auth failure/expired token, `403` lack of project role or closed form, `404` not found/out-of-project.

## Password policy
- Minimum 10 characters
- Maximum 72 characters
- At least one uppercase, one lowercase, one digit, one special (`~!@#$%^&*()_+-=,.`)
- Rejects anything that does not meet all criteria

## Route docs

### App User Auth
- [routes/app-users.md](routes/app-users.md) (create/list/update/delete)
- [routes/app-user-auth.md](routes/app-user-auth.md) (login, change/reset/revoke/active, project app-user settings)
- [routes/app-user-sessions.md](routes/app-user-sessions.md) (session history + revoke)

### Web User Auth & Security
- [routes/web-user-totp.md](routes/web-user-totp.md) (TOTP 2FA login, setup, enable/disable, backup codes)
- [routes/web-user-hardening.md](routes/web-user-hardening.md) (web user `/v1/sessions` hardening)
- [routes/lockouts.md](routes/lockouts.md) (lockout clear)

### System Configuration
- [routes/system-settings.md](routes/system-settings.md) (get/update default session settings)
- [routes/telemetry.md](routes/telemetry.md) (app user telemetry capture)
