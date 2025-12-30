# System Settings

## Get session settings (admin)
**GET /system/settings**

- Auth: Admin.
- Response — HTTP 200, application/json:
  ```json
  {
    "vg_app_user_session_ttl_days": 3,
    "vg_app_user_session_cap": 3,
    "admin_pw": "secret"
  }
  ```

## Update session settings (admin)
**PUT /system/settings**

- Auth: Admin.
- Request (JSON):
  - `vg_app_user_session_ttl_days` (optional, positive integer): Session TTL in days.
  - `vg_app_user_session_cap` (optional, positive integer): Max active sessions per app user.
  - `admin_pw` (optional, non-empty string): Admin password used by the VG app user tooling.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
- Validation:
  - `vg_app_user_session_ttl_days`/`vg_app_user_session_cap` must be positive integers.
  - Numeric strings are accepted if they are integers (for example `"3"`). Decimal strings (for example `"3.5"`) are rejected.
  - `admin_pw` must be a non-empty string when provided.
