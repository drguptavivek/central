# Lockouts

## Clear login lockouts (admin)
**POST /system/app-users/lockouts/clear**

- Auth: Admin.
- Request (JSON):
  - `username` (mandatory, string): App user username to clear.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
