# Lockouts

## Clear login lockouts (admin)
**POST /system/app-users/lockouts/clear**

- Auth: Admin.
- Request (JSON):
  - `username` (mandatory, string): App user username to clear.
  - `ip` (optional, string): Clear lockout only for this IP; when omitted, only clears lockouts recorded with a null IP.
  - Validation: `ip` must be a string when provided.
  - Validation: `username` is trimmed; whitespace-only values are rejected as missing parameters.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
