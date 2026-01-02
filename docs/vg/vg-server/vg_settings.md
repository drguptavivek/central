# VG App User Auth - Settings

> **Last Updated**: 2026-01-02

VG stores session configuration in `vg_settings`.

## Keys and defaults

- **Seeded by migration** (`server/docs/sql/vg_app_user_auth.sql`):
  - `vg_app_user_session_ttl_days` (default: 3)
  - `vg_app_user_session_cap` (default: 3)
  - `vg_app_user_lock_max_failures` (default: 5)
  - `vg_app_user_lock_window_minutes` (default: 5)
  - `vg_app_user_lock_duration_minutes` (default: 10)
  - `admin_pw` (default: `'vg_custom'`)
- **Runtime default only** (not seeded):
  - `vg_web_user_lock_duration_minutes` (default fallback: 10)

`vg_web_user_lock_duration_minutes` is read from `vg_settings` if present and a positive integer; otherwise the server falls back to `10`.

## Where settings apply

- **TTL** controls how long a bearer token remains valid.
- **Cap** controls how many active sessions an app user can have.
  - When the cap is exceeded, older sessions are revoked on login.
- **Lock settings** control app-user login throttling and lockouts.
  - Max failures within a window trigger a lock for the configured duration.
- **Web user lock duration** controls `/v1/sessions` lockout length for web users.
- **admin_pw** is included in managed QR code payloads for ODK Collect settings lock.
  - Project-level overrides are supported via `vg_project_settings`.
  - QR codes are generated dynamically from this setting.
  - Used to configure ODK Collect's settings lock feature.
  - Both "Show QR" and password reset QR codes include this value.

## Update paths

- API:
  - `GET /system/settings` returns current values for `vg_app_user_session_ttl_days`, `vg_app_user_session_cap`, `admin_pw`.
  - `PUT /system/settings` updates `vg_app_user_session_ttl_days`, `vg_app_user_session_cap`, `admin_pw`.
  - `GET /projects/:projectId/app-users/settings` returns project-effective values for `vg_app_user_session_ttl_days`, `vg_app_user_session_cap`, `admin_pw`.
  - `PUT /projects/:projectId/app-users/settings` upserts project overrides for `vg_app_user_session_ttl_days`, `vg_app_user_session_cap`, `admin_pw`.
  - `POST /system/app-users/lockouts/clear` clears app-user login lockouts (does not change configuration values).
- DB:
  - Update `vg_settings` directly for global values (including `vg_web_user_lock_duration_minutes`).
  - Update `vg_project_settings` directly for project overrides of app-user settings (TTL/cap/admin_pw) and app-user lockout settings.
    - Note: app-user lockout settings do not currently have a public API.

## Validation

- **TTL & Cap**: Stored as strings but parsed as positive integers server-side (TTL in days, cap in number of sessions).
  - DB constraints enforce positive integers for these keys in `vg_settings` and `vg_project_settings`.
- **Lock settings**: Stored as strings but parsed as positive integers server-side (max failures, window minutes, duration minutes).
  - DB constraints enforce positive integers for these keys in `vg_settings` and `vg_project_settings`.
- **Web user lock duration**: Stored as string but parsed as a positive integer server-side.
  - No DB constraint currently enforces this key; invalid/missing values fall back to `10`.
- **admin_pw**: Stored as plain text string.
  - Max length 72 characters.
  - API rejects empty/blank values; DB updates can bypass this, so keep it non-empty.
  - No complexity requirements (any string allowed).
  - No encryption (stored plain text for ODK Collect QR inclusion).

## QR Code Payload

When generating managed QR codes for app users, `admin_pw` is included in the QR payload:

```json
{
  "general": {
    "server_url": "https://central.local/v1/projects/1",
    "username": "app_user",
    "form_update_mode": "match_exactly",
    "automatic_update": true,
    "delete_send": false,
    "default_completed": false,
    "analytics": true,
    "metadata_username": "App User Display Name"
  },
  "admin": {
    "change_server": false,
    "admin_pw": "vg_custom"
  },
  "project": {
    "name": "Project Name",
    "project_id": "1"
  }
}
```

The payload is:
1. Serialized to JSON
2. Compressed via zlib DEFLATE
3. Base64 encoded
4. Encoded into QR code

**Note:** Both "Show QR" and password reset QR codes use the same payload structure and include the current `admin_pw` value.

## Access control

- `GET /system/settings` requires `config.read`.
- `PUT /system/settings` requires `config.set`.
- `GET /projects/:projectId/app-users/settings` requires `project.read`.
- `PUT /projects/:projectId/app-users/settings` requires `project.update`.
- `POST /system/app-users/lockouts/clear` requires `config.set`.
