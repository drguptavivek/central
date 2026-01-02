# VG App-User Auth API

> **Last Updated**: 2026-01-02

Short-lived, password-based auth for Collect-style app users tied to projects. Tokens are bearer-only (no cookies) and expire based on `vg_app_user_session_ttl_days` (default 3 days) stored in `vg_settings`, with optional per-project overrides.

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
- [routes/app-users.md](routes/app-users.md) (create/list/update/delete)
- [routes/app-user-auth.md](routes/app-user-auth.md) (login, change/reset/revoke/active, project app-user settings)
- [routes/app-user-sessions.md](routes/app-user-sessions.md) (session history + revoke)
- [routes/system-settings.md](routes/system-settings.md) (get/update default session settings)
- [routes/telemetry.md](routes/telemetry.md) (app user telemetry capture)
- [routes/lockouts.md](routes/lockouts.md) (lockout clear)
- [routes/web-user-hardening.md](routes/web-user-hardening.md) (web user `/v1/sessions` hardening)
