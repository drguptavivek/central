# App User Auth

## Login for short-lived token
**POST /projects/:projectId/app-users/login**

- Auth: Anonymous.
- Request (JSON):
  - `username` (mandatory, string): The app user's username.
  - `password` (mandatory, string): The app user's password.
  - `deviceId` (optional, string): Unique identifier for the device.
  - `comments` (optional, string): Metadata about the session/device (e.g., "tablet-1").
  ```json
  { "username": "collect-user", "password": "GoodPass!1X", "deviceId": "device-123", "comments": "tablet-1" }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "id": 12, "token": "abcd1234...tokenchars...", "projectId": 1, "expiresAt": "2025-12-19T16:00:00.000Z", "serverTime": "2025-12-16T16:00:01.000Z" }
  ```
  `id` is the app-user ID (Field Key actor id) needed for self-revoke/password change routes. `projectId` comes from the linked `field_keys` row (app users are always project-scoped). `expiresAt` is the ISO timestamp of the short-lived bearer token and is set from `vg_app_user_session_ttl_days`. `serverTime` is the server clock at the time the response is generated. Cookies ignored.
- Validation:
  - Missing body, missing `username`/`password`, or whitespace-only values → `400.3` `missingParameters`.
  - Non-string `username`/`password` → `400.11` `invalidDataTypeOfParameter`.
  - Non-string `deviceId`/`comments` → `400.11` `invalidDataTypeOfParameter`.
- Failure: HTTP 401.2 `authenticationFailed` (generic message).
- Lockout: defaults to 5 failed attempts in 5 minutes per `username+IP` → 10-minute lock. Attempts are logged in `vg_app_user_login_attempts` with success/failure; lockouts are tracked in `vg_app_user_lockouts`.
  - Project overrides are read from `vg_project_settings` (see `docs/vg/vg-server/vg_settings.md`).

## Change password (self)
**POST /projects/:projectId/app-users/:id/password/change**

- Auth: App user bearer token.
- Request (JSON):
  - `oldPassword` (mandatory, string): Current password for verification.
  - `newPassword` (mandatory, string): New password. Must meet complexity policy.
  ```json
  { "oldPassword": "GoodPass!1X", "newPassword": "NewPass!2Y" }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
  All sessions for that actor are terminated.
- Validation:
  - Missing or whitespace-only `oldPassword`/`newPassword` → `400.3` `missingParameters`.
  - Non-string `oldPassword`/`newPassword` → `400.11` `invalidDataTypeOfParameter`.
  - `newPassword` longer than 72 chars → `400.38` `passwordTooLong`.

## Reset password (admin)
**POST /projects/:projectId/app-users/:id/password/reset**

- Auth: Admin/manager on the project.
- Request (JSON):
  - `newPassword` (mandatory, string): New password for the user. Must meet complexity policy.
  ```json
  { "newPassword": "ResetPass!3Z" }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
  All sessions for that actor are terminated.
- Validation:
  - Missing or whitespace-only `newPassword` → `400.3` `missingParameters`.
  - Non-string `newPassword` → `400.11` `invalidDataTypeOfParameter`.
  - `newPassword` longer than 72 chars → `400.38` `passwordTooLong`.

## Revoke own sessions
**POST /projects/:projectId/app-users/:id/revoke**

- Auth: App user bearer token (self). `id` is the app-user ID returned by `/login`.
- Behavior: revokes only the current token.
- If the token belongs to a different project than `:projectId`, returns 404 (project-scoped not found).
- If the current session is missing (unexpected auth context), returns 401 authentication failed.
- Request (JSON):
  - `deviceId` (optional, string): Used for audit/logging.
- Validation:
  - Non-string `deviceId` → `400.11` `invalidDataTypeOfParameter`.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```

## Revoke sessions (admin)
**POST /projects/:projectId/app-users/:id/revoke-admin**

- Auth: Admin/manager on the project (web UI).
- If `:id` is not in the project, returns 404 (project-scoped not found).
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```

## Deactivate/reactivate app user (admin)
**POST /projects/:projectId/app-users/:id/active**

- Auth: Admin/manager on the project (web UI).
- Request (JSON):
  - `active` (mandatory, boolean): `true` to reactivate, `false` to deactivate.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
