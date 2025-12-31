# VG App User Auth - Settings

VG stores session configuration in `vg_settings`.

## Keys and defaults

- `vg_app_user_session_ttl_days` (default: 3)
- `vg_app_user_session_cap` (default: 3)
- `vg_app_user_lock_max_failures` (default: 5)
- `vg_app_user_lock_window_minutes` (default: 5)
- `vg_app_user_lock_duration_minutes` (default: 10)
- `admin_pw` (default: `'vg_custom'`)

Defaults are seeded by `server/docs/sql/vg_app_user_auth.sql`.

## Where settings apply

- **TTL** controls how long a bearer token remains valid.
- **Cap** controls how many active sessions an app user can have.
  - When the cap is exceeded, older sessions are revoked on login.
- **Lock settings** control app-user login throttling and lockouts.
  - Max failures within a window trigger a lock for the configured duration.
- **admin_pw** is included in managed QR code payloads for ODK Collect settings lock.
  - QR codes are generated dynamically from this setting.
  - Used to configure ODK Collect's settings lock feature.
  - Both "Show QR" and password reset QR codes include this value.

## Update paths

- API: `GET /system/settings` returns current values; `PUT /system/settings` updates them.
- DB: update `vg_settings` directly if needed.
  - Project overrides: update `vg_project_settings` for a specific `projectId`.

## Validation

- **TTL & Cap**: Stored as strings but parsed as numbers server-side.
  - Must be positive integers (TTL in days, cap in number of sessions).
  - DB constraint enforces positive integer values.
- **Lock settings**: Stored as strings but parsed as numbers server-side.
  - Must be positive integers (max failures, window minutes, duration minutes).
  - Project-level overrides enforce positive integers in `vg_project_settings`.
- **admin_pw**: Stored as plain text string.
  - Must be non-empty.
  - Max length 72 characters.
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
