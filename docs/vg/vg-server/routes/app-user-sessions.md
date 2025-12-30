# App User Sessions

## List app-user sessions (admin)
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
  ```

## List app-user sessions by project (admin)
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

## Revoke a single app-user session (admin)
**POST /projects/:projectId/app-users/sessions/:sessionId/revoke**

- Auth: Admin/manager on the project (web UI).
- Behavior: terminates the session and marks it inactive in history.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
