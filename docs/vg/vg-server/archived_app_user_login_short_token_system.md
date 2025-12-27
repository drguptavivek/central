# Archived: App-user login plan

This document is archived. Core behavior and implementation details are consolidated into:

- `server/docs/vg_overview.md`
- `server/docs/vg_user_behavior.md`
- `server/docs/vg_settings.md`
- `server/docs/vg_implementation.md`
- `server/docs/vg_api.md`

# Concrete backend plan for app-user login + short-lived tokens (new server, no legacy path)

  1. Schema

  - New table vg_field_key_auth (one-to-one with field_keys via actorId primary key/foreign key):
      - actorId integer primary key references field_keys("actorId") on delete cascade.
      - vg_username text not null (stored lowercase/trimmed); check lower(trim(vg_username)) = vg_username; unique; not displayName.
      - vg_password_hash (not null); store bcrypt hash.
      - vg_phone (string, normalize to E.164); nullable if not provided (validated in app).
      - vg_active boolean default true.
    Index: unique on vg_username; optional index on vg_active.
  - New table vg_settings (id serial, vg_key_name text, vg_key_value text) to store vg_app_user_session_ttl_days (days or seconds) and future vg_* configs; seed row ('vg_app_user_session_ttl_days','3').
    - Also seed vg_app_user_session_cap default 3 to cap active app-user sessions.
  - New table vg_app_user_login_attempts for tracking login failures/successes; rows retained indefinitely.
  - Migration: create new tables; no changes to field_keys columns; provided as separate SQL at docs/sql/vg_app_user_auth.sql to apply via psql.

  2. App User create/update API (/projects/:projectId/app-users)

  - Require payload: { username, password, fullName (displayName), phone?, active? } (maps to vg_* columns).
  - Enforce password policy: min 10 chars; at least one upper, one lower, one digit, one special from
    ~!@#$%^&*()_+-=,. ; reject otherwise.
  - Hash password with existing user bcrypt helper before storing.
  - Enforce username uniqueness per constraint; never reuse displayName for login.
  - Do NOT auto-issue long-lived tokens; only short-lived sessions via login endpoint.
  - Allow update of phone, fullName, active; password change via dedicated endpoint only.

  3. Login endpoint

  - Route: POST /projects/:projectId/app-users/login.
  - Payload: { username, password } (no displayName lookup).
  - Look up by global username; verify hash; reject inactive accounts.
  - Rate limiting/throttling per username+IP; lockout after 5 failed attempts within 5 minutes; lock duration 10 minutes; store events in vg_app_user_login_attempts.
  - On success: Sessions.create(actor, expiresAt = now + server-config TTL); return { token, projectId } and
    optionally managed QR JSON.
  - On failure: generic auth failed; audit events for success/failure.

  4. Password change/reset

  - Change (self): POST /projects/:projectId/app-users/:id/password/change with { oldPassword, newPassword };
    enforce policy; verify old password; rotate all sessions for that actor; audit.
  - Reset (admin): POST /projects/:projectId/app-users/:id/password/reset with { newPassword } (or forced reset
    flag); enforce policy; rotate sessions; audit; deliver password out-of-band if needed.

  5. Revocation and deactivate

  - Self revoke: POST /projects/:projectId/app-users/:id/revoke; only allowed if authenticated actor matches
    target; terminates all sessions for that actor including current token.
  - Admin revoke: POST /projects/:projectId/app-users/:id/revoke-admin; requires admin privilege; terminates all
    sessions for target.
  - Deactivate/reactivate (admin): toggle active flag; on deactivate, terminate all sessions; audit.

  6. Session issuance defaults

  - FieldKeys.create never issues long-lived tokens.
  - Sessions.create reads TTL from DB config; no sliding refresh unless explicitly added later.

  7. Auth handler

  - No change needed for /key/<token>; it already validates sessions and expiry.
  - Reject auth for inactive accounts even if token exists.

  8. Browser and app clients

  - Endpoints are callable from browsers (admins or app-user self-service) and from Collect.
  - Prefer header/bearer token auth and avoid cookies on these routes to remove CSRF surface.
  - If cookies ever used for admin UI, set SameSite=Lax/Strict and require a CSRF token (double-submit or
    synchronizer token) and reject requests missing the CSRF header/token. Consider CORS restrictions for admin
    UI origin.
  - Collect continues to send JSON bodies + Authorization header; ensure cookies are ignored for login routes.

  9. Audit and telemetry

  - Audit: create/update/deactivate/reactivate, password change/reset, login success/failure, session
    issued/revoked, config TTL changes; include actor, target, IP/device, timestamp. Namespaced action identifiers
    vg_* for new events. Implemented via `container.Audits.log` in domain layer: vg.app_user.create/login.success/
    login.failure/password.change/password.reset/sessions.revoke/activate/deactivate. Requires `actors` acteeId,
    so vg auth queries join actors to carry acteeId for audit payloads. Ensure `Audits` is injected into vg
    resources/domain calls.
  - Monitoring: log rate-limit events and lockouts.

 10. Namespacing for code artifacts

  - New modules/helpers, functions, and audit action identifiers use vg_ prefixes (e.g., vg_app_user_passwords,
    vg_app_user_auth, vg_app_user_rate_limit) to reduce collision risk on future upstream changes.

## Open questions

- Session TTL default set to 3 days in config.

## 11. Implementation Updates (2025-12-17)

### System Settings API
To support the Admin Settings UI, the following endpoints were implemented in `server/lib/resources/vg-app-user-auth.js`:

-   **GET /system/settings**: Retrieves current session configuration (`vg_app_user_session_ttl_days`, `vg_app_user_session_cap`).
    -   **Access**: Requires `config.read` permission (Admin).
    -   **Purpose**: Allows the frontend to display current settings to administrators.
-   **PUT /system/settings**: Updates session configuration.
    -   **Access**: Requires `config.set` permission (Admin).
    -   **Purpose**: Allows administrators to modify session TTL and concurrency caps.

### Database Changes
-   **`vg_settings` Table**: Confirmed existence and usage for storing `vg_app_user_session_ttl_days` and `vg_app_user_session_cap`.
-   **`upsertSetting` Query**: Added to `server/lib/model/query/vg-app-user-auth.js` to handle safe updates (insert or update on conflict) for configuration keys.

### Reason & Purpose
These changes were necessary to fulfill the requirement of an "Admin Settings UI" where administrators can configure App User session behavior without direct database access. This completes the management loop for the short-lived token system.
