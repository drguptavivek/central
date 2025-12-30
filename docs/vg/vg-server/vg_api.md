# VG App-User Auth API

Short-lived, password-based auth for Collect-style app users tied to projects. Tokens are bearer-only (no cookies) and expire based on `vg_app_user_session_ttl_days` (default 3 days) stored in `vg_settings`.

## Frontend quick reference
- No long-lived tokens are ever returned from create/list endpoints; only `/login` returns a short-lived bearer token.
- Listings always include `token: null`; use `/login` to obtain a token for data submission.
- Session cap and TTL are enforced server-side; a new login trims older sessions beyond the cap.
- All app-user requests must include `Authorization: Bearer <short-token>` (never cookies).
- Common error codes: `400` validation, `401` auth failure/expired token, `403` lack of project role or closed form, `404` not found/out-of-project.

## Password policy
- Minimum 10 characters
- At least one uppercase, one lowercase, one digit, one special (`~!@#$%^&*()_+-=,.`)
- Rejects anything that does not meet all criteria

## Route docs
- `docs/vg/vg-server/routes/app-users.md` (create/list/update/delete)
- `docs/vg/vg-server/routes/app-user-auth.md` (login, change/reset/revoke/active)
- `docs/vg/vg-server/routes/app-user-sessions.md` (session history + revoke)
- `docs/vg/vg-server/routes/system-settings.md` (get/update session settings)
- `docs/vg/vg-server/routes/telemetry.md` (app user telemetry capture)
- `docs/vg/vg-server/routes/lockouts.md` (lockout clear)
