# App Users

## Create app user
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

## List app users
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

## Update app user (name/phone)
**PATCH /projects/:projectId/app-users/:id**

- Auth: Admin/manager on the project.
- Request (JSON):
  - `fullName` (optional, string): New display name.
  - `phone` (optional, string): New contact number (max 25 chars).
  ```json
  { "fullName": "New Name", "phone": "+15557654321" }
  ```
  `fullName` must be a non-empty string; `phone` is trimmed and capped at 25 characters. `username` is immutable once created.
- Validation:
  - At least one of `fullName` or `phone` is required; missing both returns `400.3` `missingParameters`.
  - Non-string `fullName`/`phone` → `400.11` `invalidDataTypeOfParameter`.
  - Whitespace-only `phone` is normalized to `null`.
- Response — HTTP 200, application/json (no token is ever returned):
  ```json
  { "id": 12, "projectId": 1, "displayName": "New Name", "phone": "+15557654321", "active": true, "username": "collect-user", "token": null }
  ```

## Delete app user
**DELETE /projects/:projectId/app-users/:id**

- Auth: Admin/manager on the project.
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```
