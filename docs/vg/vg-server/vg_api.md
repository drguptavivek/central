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

## Endpoints

### Create app user
**POST /projects/:projectId/app-users**

- Auth: Admin/manager on the project.
- Request (JSON):
  - `username` (mandatory, string): Unique login identifier. Normalized to lowercase.
  - `password` (mandatory, string): Initial password. Must meet complexity policy.
  - `fullName` (mandatory, string): Display name for the user.
  - `phone` (optional, string): Contact number (max 25 chars).
  - `active` (optional, boolean): Initial account status. Defaults to `true`.
  ```json
  { "username": "collect-user", "password": "GoodPass!1X", "fullName": "Collect User", "phone": "+15551234567", "active": true }
  ```
- Response — HTTP 200, application/json (app-user record; no long-lived token is minted):
  ```json
  { "id": 12, "createdAt": "2025-12-16T16:00:00.000Z", "updatedAt": null, "displayName": "Collect User", "token": null, "projectId": 1, "active": true }
  ```

### Login for short-lived token
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
- Failure: HTTP 401.2 `authenticationFailed` (generic message).
- Lockout: 5 failed attempts in 5 minutes per `username+IP` → 10-minute lock. Attempts are logged in `vg_app_user_login_attempts` with success/failure.

### List app users
**GET /projects/:projectId/app-users**

- Auth: Admin/manager on the project.
- Response — HTTP 200, application/json:
  ```json
  [
    {
      "id": 12,
      "projectId": 1,
      "displayName": "Collect User",
      "createdAt": "2025-12-16T16:00:00.000Z",
      "updatedAt": null,
      "token": null,
      "active": true,
      "username": "collect-user",
      "phone": "+15551234567"
    }
  ]
  ```
  `token` is always `null` in listings; use `/login` for a short-lived token. Extended metadata (`X-Extended-Metadata: true`) also returns `createdBy` and `lastUsed`.

### Update app user (name/phone)
**PATCH /projects/:projectId/app-users/:id**

- Auth: Admin/manager on the project.
- Request (JSON):
  - `fullName` (optional, string): New display name.
  - `phone` (optional, string): New contact number (max 25 chars).
  ```json
  { "fullName": "New Name", "phone": "+15557654321" }
  ```
  `fullName` must be a non-empty string; `phone` is trimmed and capped at 25 characters. `username` is immutable once created.
- Response — HTTP 200, application/json (no token is ever returned):
  ```json
  { "id": 12, "projectId": 1, "displayName": "New Name", "phone": "+15557654321", "active": true, "username": "collect-user", "token": null }
  ```

### Change password (self)
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

### Reset password (admin)
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

### Revoke own sessions
**POST /projects/:projectId/app-users/:id/revoke**

- Auth: App user bearer token (self). `id` is the app-user ID returned by `/login`.
- Behavior: revokes only the current token.
- Request (JSON): 
  - `deviceId` (optional, string): Used for audit/logging.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```

### Revoke sessions (admin)
**POST /projects/:projectId/app-users/:id/revoke-admin**

- Auth: Admin/manager on the project (web UI).
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```

### List app-user sessions (admin)
**GET /projects/:projectId/app-users/:id/sessions**

- Auth: Admin/manager on the project (web UI).
- Query params:
  - `limit` (optional, integer): Pagination limit.
  - `offset` (optional, integer): Pagination offset.
- Response header: `X-Total-Count` for total sessions matching the filter.
- Returns session history for the app user (including expired sessions).
- Response — HTTP 200, application/json:
  ```json
  [
    { "id": 10, "createdAt": "2025-12-16T16:00:00.000Z", "expiresAt": "2025-12-19T16:00:00.000Z", "ip": "127.0.0.1", "userAgent": "Collect/1.0", "deviceId": "device-123", "comments": "tablet-1" }
  ]

### List app-user sessions by project (admin)
**GET /projects/:projectId/app-users/sessions**

- Auth: Admin/manager on the project (web UI).
- Query params:
  - `appUserId` (optional, integer): Filter by a specific app user.
  - `dateFrom` (optional, ISO datetime): Filter by creation time start.
  - `dateTo` (optional, ISO datetime): Filter by creation time end.
  - `limit` (optional, integer): Pagination limit.
  - `offset` (optional, integer): Pagination offset.
- Response header: `X-Total-Count` for total sessions matching the filter.
- Returns session history (including expired sessions).
- Response — HTTP 200, application/json:
  ```json
  [
    { "id": 10, "appUserId": 12, "createdAt": "2025-12-16T16:00:00.000Z", "expiresAt": "2025-12-19T16:00:00.000Z", "ip": "127.0.0.1", "userAgent": "Collect/1.0", "deviceId": "device-123", "comments": "tablet-1" }
  ]
  ```

### Revoke a single app-user session (admin)
**POST /projects/:projectId/app-users/sessions/:sessionId/revoke**

- Auth: Admin/manager on the project (web UI).
- Behavior: terminates the session and marks it inactive in history.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
  ```

### Submit telemetry (app user)
**POST /projects/:projectId/app-users/telemetry**

- Auth: App user bearer token (Collect).
- Request (JSON):
  - `deviceId` (mandatory, string): Unique identifier for the device.
  - `collectVersion` (mandatory, string): Version string of the Collect app.
  - `deviceDateTime` (mandatory, ISO datetime): UTC timestamp generated by the device.
  - `location` (optional, object): Geographic coordinates.
    - `latitude` (mandatory if location present, number): Latitude in decimal degrees.
    - `longitude` (mandatory if location present, number): Longitude in decimal degrees.
    - `altitude` (optional, number): Altitude in meters.
    - `accuracy` (optional, number): Horizontal accuracy in meters.
    - `speed` (optional, number): Speed in meters per second.
    - `bearing` (optional, number): Bearing in degrees.
    - `provider` (optional, string): Source of the location (e.g., "gps").
  - `event` (optional, object): Single client event payload (see below).
  - `events` (optional, array): Batch of up to 10 events; cannot be provided with `event`.
- Event object:
  - `id` (mandatory, string): Client-generated stable id for dedupe.
  - `type` (mandatory, string): Event type identifier.
  - `occurredAt` (optional, ISO datetime): UTC timestamp when the event occurred.
  - `details` (optional, object): Arbitrary event details.
  - Additional metadata is stored as-is.
- Idempotency: events are upserted on `(appUserId/actorId, deviceId, event.id)` so offline retries do not create duplicates.
- App users only; web users cannot submit telemetry on their behalf.
- `appUserId` (optional, integer) must match the authenticated app user if provided.
- If the bearer token belongs to a different project than `:projectId`, the endpoint returns 404 (project scoped not found).
  ```json
  {
    "deviceId": "device-123",
    "collectVersion": "Collect/2025.1",
    "deviceDateTime": "2025-12-21T10:00:00.000Z",
    "location": {
      "latitude": 37.7749,
      "longitude": -122.4194,
      "altitude": 10.5,
      "accuracy": 3.2,
      "speed": 0.5,
      "bearing": 42.1,
      "provider": "gps"
    },
    "event": {
      "id": "evt-001",
      "type": "form_opened",
      "occurredAt": "2025-12-21T09:59:00.000Z",
      "details": { "formId": "registration" }
    }
  }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "id": 55, "appUserId": 12, "deviceId": "device-123", "dateTime": "2025-12-21T10:02:00.000Z", "serverTime": "2025-12-21T10:02:00.500Z", "status": "ok", "clientEventId": "evt-001" }
  ```
  `deviceDateTime` is device-generated; `dateTime` is the server receive time recorded with the row; `serverTime` is the server clock at the time the response is generated.
  `status` is `ok` or `invalidated` if the bearer token no longer resolves to an active session by the time the record is processed. `clientEventId` is returned only when an event was provided.
  For `events` batches, the response is an array of result rows (one per event), each with `id`, `appUserId`, `deviceId`, `clientEventId`, `dateTime`, `serverTime`, and `status`.

### List telemetry (system admin)
**GET /system/app-users/telemetry**

- Auth: Requires `config.read` permission.
- Query params:
  - `projectId` (optional, integer): Filter by project ID.
  - `deviceId` (optional, string): Filter by device ID.
  - `appUserId` (optional, integer): Filter by app user ID.
  - `dateFrom` (optional, ISO datetime): Filter by server receive time start.
  - `dateTo` (optional, ISO datetime): Filter by server receive time end.
  - `limit` (optional, integer): Pagination limit.
  - `offset` (optional, integer): Pagination offset.
- Response header: `X-Total-Count` for total rows matching filters.
  - Response — HTTP 200, application/json:
  ```json
  [
    {
      "id": 55,
      "appUserId": 12,
      "projectId": 1,
      "deviceId": "device-123",
      "collectVersion": "Collect/2025.1",
      "deviceDateTime": "2025-12-21T10:00:00.000Z",
      "dateTime": "2025-12-21T10:02:00.000Z",
      "clientEventId": "evt-001",
      "event": { "id": "evt-001", "type": "form_opened", "occurredAt": "2025-12-21T09:59:00.000Z", "details": { "formId": "registration" } },
      "location": {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 10.5,
        "accuracy": 3.2,
        "speed": 0.5,
        "bearing": 42.1,
        "provider": "gps"
      }
    }
  ]
  ```

### Activate/deactivate
**POST /projects/:projectId/app-users/:id/active**

- Auth: Admin/manager on the project.
- Request (JSON):
  - `active` (mandatory, boolean): `false` to deactivate, `true` to reactivate.
  ```json
  { "active": false }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
  Setting `active: false` deactivates and terminates sessions; deactivated users cannot log in or be authenticated.

## Expected behavior
- Sessions remain valid only while `vg_field_key_auth.vg_active` is true and until `expiresAt` (no sliding refresh).
- Project linkage is enforced: the login response carries the app user's `projectId`, and existing sessions are only usable while the related `field_key` stays active for that project.
- All auth checks use bearer headers; cookies are ignored on these routes to minimize CSRF surface.
- Audit events for creation, password operations, revocation, activation, and login success/failure should be emitted with vg-prefixed action identifiers.
- Listings never expose active short tokens; frontends must explicitly call `/login` to obtain one for submissions.

## Configuration
- Session TTL is driven by the DB setting `vg_app_user_session_ttl_days` stored in `vg_settings`; default seed is `3` days (see migration `docs/sql/vg_app_user_auth.sql`). If the setting is absent, the backend falls back to 3 days.
- Session cap is driven by DB setting `vg_app_user_session_cap` in `vg_settings`; default seed is `3` active sessions per app user. Each login trims older sessions beyond the cap.

## System settings (admin)

### Get session settings
**GET /system/settings**

- Auth: Requires `config.read` permission.
- Response — HTTP 200, application/json:
  ```json
  { "vg_app_user_session_ttl_days": 3, "vg_app_user_session_cap": 3, "admin_pw": "current_password" }
  ```

### Update session settings
**PUT /system/settings**

- Auth: Requires `config.set` permission.
- Request (JSON):
  - `vg_app_user_session_ttl_days` (optional, integer): New TTL in days.
  - `vg_app_user_session_cap` (optional, integer): New session concurrency cap.
  - `admin_pw` (optional, string): New admin password for Collect settings.
  ```json
  { "vg_app_user_session_ttl_days": 5, "vg_app_user_session_cap": 2, "admin_pw": "new_password" }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```

## Lockouts (admin)

### Clear lockout
**POST /system/app-users/lockouts/clear**

- Auth: Requires `config.set` permission.
- Request (JSON):
  - `username` (mandatory, string): Target username to unlock.
  - `ip` (optional, string): Specific IP to unlock. If omitted, clears all lockouts for the username.
  ```json
  { "username": "collect-user", "ip": "1.2.3.4" }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
