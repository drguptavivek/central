# System Settings

## Get session settings (admin)
**GET /system/settings**

- Auth: Admin.
- Note: Values are global defaults. Project-level overrides are managed via `GET/PUT /projects/:projectId/app-users/settings`.
- Response — HTTP 200, application/json:
  ```json
  {
    "vg_app_user_session_ttl_days": 3,
    "vg_app_user_session_cap": 3,
    "vg_app_user_ip_max_failures": 20,
    "vg_app_user_ip_window_minutes": 15,
    "vg_app_user_ip_lock_duration_minutes": 30,
    "admin_pw": "secret"
  }
  ```

## Update session settings (admin)
**PUT /system/settings**

- Auth: Admin.
- Note: Updates global defaults. Project-level overrides use `PUT /projects/:projectId/app-users/settings`.
- Request (JSON):
  - `vg_app_user_session_ttl_days` (optional, positive integer): Session TTL in days.
  - `vg_app_user_session_cap` (optional, positive integer): Max active sessions per app user.
  - `vg_app_user_ip_max_failures` (optional, positive integer): Max failed login attempts per IP before lockout.
  - `vg_app_user_ip_window_minutes` (optional, positive integer): Time window in minutes for counting IP failures.
  - `vg_app_user_ip_lock_duration_minutes` (optional, positive integer): IP lockout duration in minutes.
  - `admin_pw` (optional, non-empty string, max 72 chars): Admin password used by the VG app user tooling.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
- Validation:
  - At least one setting must be provided; missing all returns `400.3` `missingParameters`.
  - Numeric settings (`vg_app_user_session_ttl_days`, `vg_app_user_session_cap`, `vg_app_user_ip_max_failures`, `vg_app_user_ip_window_minutes`, `vg_app_user_ip_lock_duration_minutes`) must be positive integers.
  - Numeric strings are accepted if they are integers (for example `"3"`). Decimal strings (for example `"3.5"`) are rejected.
  - `admin_pw` must be a non-empty string when provided, with a max length of 72 characters.
