# Enketo Status

## Get Enketo status for all forms (admin)
**GET /v1/system/enketo-status**

- Auth: Admin (requires `config.read` permission).
- Query Parameters (optional):
  - `projectId` (integer): Filter by project ID
  - `xmlFormId` (string): Filter by form XML ID
- Response — HTTP 200, application/json:
  ```json
  {
    "data": [
      {
        "projectId": 1,
        "projectName": "My Project",
        "formId": 2,
        "xmlFormId": "my_form",
        "formName": "My Form",
        "state": "open",
        "enketoId": "abc123",
        "enketoOnceId": "xyz789",
        "lastUpdatedAt": "2026-01-03T00:06:26.000Z",
        "status": "healthy",
        "reason": "Has Enketo ID"
      }
    ],
    "meta": {
      "total": 10,
      "healthy": 3,
      "never_pushed": 5,
      "draft_only": 1,
      "closed": 1
    }
  }
  ```

### Status Categories

| Status | Description | Can Regenerate |
|--------|-------------|----------------|
| `healthy` | Form has both `enketoId` and `enketoOnceId` | No |
| `never_pushed` | Form's `enketoId` is NULL (never pushed to Enketo) | Yes |
| `draft_only` | Only the draft version has an `enketoId`, published form doesn't | No |
| `closed` | Form state is not 'open' | No |
| `push_failed` | Last push attempt to Enketo failed | Yes |

---

## Regenerate Enketo IDs (admin)
**POST /v1/system/enketo-status/regenerate**

- Auth: Admin (requires `config.set` permission).
- Request (JSON):
  ```json
  {
    "forms": [
      {
        "formId": 2,
        "projectId": 1
      },
      {
        "formId": 5,
        "projectId": 1
      }
    ]
  }
  ```
- Response — HTTP 200, application/json:
  ```json
  {
    "results": [
      {
        "formId": 2,
        "xmlFormId": "my_form",
        "success": true,
        "oldEnketoId": null,
        "newEnketoId": "newAbc123"
      }
    ],
    "errors": [
      {
        "formId": 5,
        "success": false,
        "error": "Form is closed, cannot regenerate Enketo ID"
      }
    ]
  }
  ```

### Validation and Behavior

- Only forms with status `never_pushed` or `push_failed` can be regenerated
- Closed forms (state != 'open') cannot be regenerated
- Draft-only forms cannot be regenerated (publish the draft instead)
- Returns results for successful regenerations and errors for failed attempts
- Forms with existing healthy Enketo IDs can be included but will succeed with the same ID

### Implementation Notes

- Uses the existing `Forms.pushFormToEnketo()` function with retry count of 5
- Updates both `enketoId` and `enketoOnceId` in the forms table
- Triggers audit logging for each regeneration attempt
- Bulk operations run in parallel using `Promise.all()`
