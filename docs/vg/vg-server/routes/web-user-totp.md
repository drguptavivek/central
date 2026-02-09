# Web User TOTP 2FA

## Login Phase 1: Email + Password
**POST /v1/sessions**

- Auth: Anonymous.
- Request (JSON):
  - `email` (mandatory, string): The user's email address.
  - `password` (mandatory, string): The user's password.
  ```json
  { "email": "user@example.com", "password": "SecurePass!123" }
  ```
- Response (No TOTP) — HTTP 200, application/json:
  ```json
  {
    "actorId": 5,
    "token": "WlHP4MlKyhIwowR6YhV7bQTG...",
    "expiresAt": "2026-02-09T08:32:29.843Z",
    "createdAt": "2026-02-08T08:32:29.848Z",
    "csrf": "AKOPikMi2RTj2v$Jg2j6yC...",
    "totp_verified": true
  }
  ```
  Session cookies are set (HttpOnly, Secure, SameSite=Strict). User is fully authenticated.

- Response (TOTP Required) — HTTP 200, application/json:
  ```json
  {
    "actorId": 5,
    "token": "WlHP4MlKyhIwowR6YhV7bQTG...",
    "expiresAt": "2026-02-08T08:33:29.843Z",
    "createdAt": "2026-02-08T08:32:29.848Z",
    "csrf": "AKOPikMi2RTj2v$Jg2j6yC...",
    "totp_verified": false,
    "requireTotp": true
  }
  ```
  **⚠️ No cookies set.** Token expires in 60 seconds. Frontend must send as Bearer token in Phase 2. Token only valid for `/sessions/totp-verify` endpoint.

- Validation:
  - Missing `email` or `password` → `400.3` `missingParameters`.
  - Invalid credentials → `401.2` `authenticationFailed`.
- Lockout: 5 failed attempts in 5 minutes per `email+IP` → 10-minute lock.

## Login Phase 2: TOTP Verification
**POST /v1/sessions/totp-verify**

- Auth: Bearer token (from Phase 1 response).
- Headers:
  ```
  Authorization: Bearer WlHP4MlKyhIwowR6YhV7bQTG...
  ```
- Request (JSON):
  - `token` (mandatory, string): 6-digit TOTP code from authenticator app OR 8-character backup code.
  ```json
  { "token": "123456" }
  ```
- Response — HTTP 200, application/json:
  ```json
  {
    "token": "WlHP4MlKyhIwowR6YhV7bQTG...",
    "csrf": "cfktRm90a5NZN0j4SEcOnSF8S3s...",
    "expiresAt": "2026-02-09T08:43:10.889Z",
    "createdAt": "2026-02-08T04:49:24.263Z",
    "id": 5,
    "type": "user",
    "displayName": "user@example.com",
    "updatedAt": null,
    "deletedAt": null
  }
  ```
  Session cookies are NOW set. Session expiration extended to full `sessionLifetime` (was 60s, now ~24h). User is fully authenticated.

- Validation:
  - Missing `token` → `400.3` `missingParameters`.
  - Non-string `token` → `400.11` `invalidDataTypeOfParameter`.
  - Invalid TOTP code → `401.7` `invalidTotpCode`.
  - Session already verified → `400.28` `alreadyActive`.
  - Session expired (>60s since Phase 1) → `401.2` `authenticationFailed`.
- Rate Limiting: 5 failed TOTP attempts per 5 minutes per IP → 10-minute lock.

## Setup TOTP (Begin Enrollment)
**POST /v1/users/:id/totp/setup**

- Auth: Web user session (self) or admin.
- Permissions: User can setup their own TOTP, or admin can setup for others.
- Response — HTTP 200, application/json:
  ```json
  {
    "secret": "JBSWY3DPEBLW64TMMQ======",
    "qrCode": "data:image/png;base64,iVBORw0KGgo...",
    "backupCodes": [
      "BACKUP-0001",
      "BACKUP-0002",
      "...",
      "BACKUP-0010"
    ]
  }
  ```
  `secret` is Base32-encoded TOTP secret. `qrCode` is PNG data URL for scanning. `backupCodes` are 10 single-use recovery codes. **Does NOT save to database yet** (temporary setup state).

## Enable TOTP (Verify First Code)
**POST /v1/users/:id/totp/enable**

- Auth: Web user session (self) or admin.
- Request (JSON):
  - `token` (mandatory, string): 6-digit code from authenticator app.
  ```json
  { "token": "123456" }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "ok": true }
  ```
  TOTP is now enabled. Secret and backup codes saved to database. `totp_enabled = true`.

- Validation:
  - Missing `token` → `400.3` `missingParameters`.
  - Non-string `token` → `400.11` `invalidDataTypeOfParameter`.
  - Invalid code → `401.7` `invalidTotpCode`.

## Disable TOTP
**POST /v1/users/:id/totp/disable**

- Auth: Web user session (self) or admin.
- Request (JSON):
  - `password` (mandatory, string): User's password for verification.
  ```json
  { "password": "SecurePass!123" }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "ok": true }
  ```
  TOTP is now disabled. `totp_enabled = false`, backup codes cleared.

- Validation:
  - Missing `password` → `400.3` `missingParameters`.
  - Non-string `password` → `400.11` `invalidDataTypeOfParameter`.
  - Incorrect password → `401.2` `authenticationFailed`.

## Regenerate Backup Codes
**POST /v1/users/:id/totp/backup-codes/regenerate**

- Auth: Web user session (self) or admin.
- Request (JSON):
  - `password` (mandatory, string): User's password for verification.
  ```json
  { "password": "SecurePass!123" }
  ```
- Response — HTTP 200, application/json:
  ```json
  {
    "backupCodes": [
      "NEWCODE-01",
      "NEWCODE-02",
      "...",
      "NEWCODE-10"
    ]
  }
  ```
  Old backup codes are invalidated. New codes saved to database (encrypted).

- Validation:
  - Missing `password` → `400.3` `missingParameters`.
  - Non-string `password` → `400.11` `invalidDataTypeOfParameter`.
  - Incorrect password → `401.2` `authenticationFailed`.

## Get TOTP Status
**GET /v1/users/:id/totp/status**

- Auth: Web user session (self) or admin.
- Permissions: User can check their own status. Admin can check any user.
- Response — HTTP 200, application/json:
  ```json
  {
    "enabled": true,
    "enabledAt": "2026-01-15T10:30:00Z"
  }
  ```
  `enabled` is boolean. `enabledAt` is ISO timestamp when TOTP was enabled, or `null` if not enabled.

## Session Restore
**GET /v1/sessions/restore**

- Auth: Session cookie.
- Response — HTTP 200, application/json:
  ```json
  {
    "createdAt": "2026-02-08T08:02:50.466Z",
    "expiresAt": "2026-02-09T08:02:50.466Z",
    "totp_verified": true
  }
  ```
  If `totp_verified: false`, frontend must clear session and redirect to login (TOTP verification incomplete).

- Error Response (TOTP Not Verified) — HTTP 403:
  ```json
  {
    "code": 403,
    "message": "Insufficient rights."
  }
  ```
  Returned when user has TOTP enabled but session is not verified. Middleware blocks access.

## Error Codes

| Code | HTTP | Meaning | User Action |
|------|------|---------|-------------|
| `401.7` | 401 | Invalid TOTP code | Enter correct code from authenticator app |
| `401.2` | 401 | Incorrect password or invalid session | Check password or re-login |
| `400.13` | 400 | Backup code already used | Use different backup code |
| `400.28` | 400 | TOTP already verified | Session is already authenticated |
| `429.1` | 429 | Too many attempts | Wait 10 minutes before retrying |
| `403` | 403 | TOTP required but not verified | Complete TOTP verification at `/sessions/totp-verify` |

## Security Notes

1. **Phase 1 (Password):**
   - No cookies set if TOTP enabled
   - Token returned in response body only
   - Token expires in 60 seconds
   - Token only valid for `/sessions/totp-verify`

2. **Phase 2 (TOTP):**
   - Requires Bearer authentication
   - Cookies set only after successful verification
   - Session expiration extended to full duration

3. **Page Refresh Protection:**
   - Refreshing during TOTP phase loses token (stored in memory)
   - User must re-login with password
   - Prevents TOTP bypass attack

4. **Middleware Protection:**
   - All endpoints except whitelist return 403 when `totp_verified=false`
   - Whitelist: `/users/:id/totp/*`, `/sessions/totp-verify`

5. **Backup Codes:**
   - Single-use only (marked in database after use)
   - 8-character alphanumeric (high entropy)
   - 10 codes per user
   - Encrypted at rest

---

## Enrollment Prompts & Mandatory 2FA

### Dismiss Enrollment Prompt
**POST /v1/users/:id/totp/dismiss-enrollment-prompt**

- Auth: Web user session (self) or admin.
- Permissions: User can dismiss their own prompt. Admin can dismiss for others.
- Request (JSON):
  - `remindAfterDays` (optional, number or null): Days until next reminder. Null = permanent dismissal.
  ```json
  { "remindAfterDays": 7 }
  ```
  or
  ```json
  { "remindAfterDays": null }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```

- Validation:
  - `remindAfterDays` must be number 1-365 or null → `400.11` `invalidDataTypeOfParameter`
  - User's role in mandatory roles list → `403` `insufficientRights` (cannot dismiss)

**Behavior:**
- `remindAfterDays: 7` → Sets `totp_prompt_remind_after` to 7 days from now
- `remindAfterDays: null` → Sets `totp_prompt_dismissed_at` to now (permanent)
- Mandatory roles cannot dismiss (403 error)

---

### Get Mandatory Roles Configuration
**GET /v1/system/settings/totp-mandatory-roles**

- Auth: Web user session with `config.read` permission (admin only).
- Response — HTTP 200, application/json:
  ```json
  {
    "mandatoryRoles": ["admin", "manager"]
  }
  ```

**Purpose:** Returns list of roles that require mandatory TOTP enrollment.

---

### Update Mandatory Roles Configuration
**PUT /v1/system/settings/totp-mandatory-roles**

- Auth: Web user session with `config.set` permission (admin only).
- Request (JSON):
  - `mandatoryRoles` (mandatory, array of strings): Role IDs that require 2FA.
  ```json
  {
    "mandatoryRoles": ["admin"]
  }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "success": true }
  ```

- Validation:
  - `mandatoryRoles` must be array of strings → `400.11` `invalidDataTypeOfParameter`
  - All roles must exist in system → `400.11` `invalidDataTypeOfParameter`

**Effect:** Updates `vg_settings` table with new mandatory roles. Users in these roles will be forced to set up TOTP on next login if they don't have it enabled.

---

## Login Response Flags (Enrollment)

### Standard Login Response (No TOTP)
**POST /v1/sessions** (when user has no TOTP enabled)

**Response A** (Non-mandatory role, should prompt):
```json
{
  "actorId": 5,
  "token": "WlHP4MlKyhIwowR6YhV7bQTG...",
  "expiresAt": "2026-02-09T08:32:29.843Z",
  "createdAt": "2026-02-08T08:32:29.848Z",
  "csrf": "AKOPikMi2RTj2v$Jg2j6yC...",
  "totp_verified": true,
  "shouldPromptTotpEnrollment": true
}
```
Cookies are set. User proceeds to dashboard where optional enrollment modal is shown.

**Response B** (Non-mandatory role, already dismissed):
```json
{
  "actorId": 5,
  "token": "WlHP4MlKyhIwowR6YhV7bQTG...",
  "expiresAt": "2026-02-09T08:32:29.843Z",
  "createdAt": "2026-02-08T08:32:29.848Z",
  "csrf": "AKOPikMi2RTj2v$Jg2j6yC...",
  "totp_verified": true,
  "shouldPromptTotpEnrollment": false
}
```
User dismissed prompt. No modal shown.

**Response C** (Mandatory role, 2FA setup required):
```json
{
  "actorId": 5,
  "token": "WlHP4MlKyhIwowR6YhV7bQTG...",
  "expiresAt": "2026-02-08T08:37:29.843Z",
  "createdAt": "2026-02-08T08:32:29.848Z",
  "csrf": "AKOPikMi2RTj2v$Jg2j6yC...",
  "totp_verified": false,
  "requireTotpSetup": true,
  "mandatory": true
}
```
⚠️ **No cookies set.** Token expires in 5 minutes. User cannot proceed until TOTP is set up. Frontend shows forced setup modal (non-dismissible).

**Key differences from existing flows:**
- `requireTotp: true` = User has 2FA enabled, needs to verify code (existing flow)
- `requireTotpSetup: true` = User's role requires 2FA but they haven't set it up yet (NEW)
- Both have `totp_verified: false` and no cookies set
- Both are temporary sessions, but different purposes

---

## Enrollment: Dismiss Prompt
**POST /v1/users/:id/totp/dismiss-enrollment-prompt**

- Auth: Web user session (user can dismiss own, admin can dismiss others).
- Request (JSON):
  - `remindAfterDays` (optional, integer or null): Days until next reminder (1-365), or null for permanent dismissal.
  ```json
  { "remindAfterDays": 7 }  // Remind in 7 days
  ```
  ```json
  { "remindAfterDays": null }  // Never remind (permanent)
  ```
- Response — HTTP 200, application/json:
  ```json
  { "ok": true }
  ```
- Error Responses:
  - User has mandatory role (cannot dismiss) → `403` `insufficientRights`.
  - Invalid `remindAfterDays` (< 1 or > 365) → `400` `unexpectedValue`.
  - Missing permissions → `403` `insufficientRights`.

---

## System Settings: Get Mandatory Roles
**GET /v1/system/settings/totp-mandatory-roles**

- Auth: Admin (requires `config.read` permission).
- Response — HTTP 200, application/json:
  ```json
  {
    "mandatoryRoles": ["admin", "manager"]
  }
  ```
- Default: `["admin"]` if not configured.

---

## System Settings: Update Mandatory Roles
**PUT /v1/system/settings/totp-mandatory-roles**

- Auth: Admin (requires `config.set` permission).
- Request (JSON):
  - `mandatoryRoles` (mandatory, array of strings): List of role system names requiring mandatory 2FA.
  ```json
  {
    "mandatoryRoles": ["admin", "manager"]
  }
  ```
- Response — HTTP 200, application/json:
  ```json
  { "ok": true }
  ```
- Error Responses:
  - Invalid role names (not in system roles) → `400` `unexpectedValue`.
  - Not an array or contains non-strings → `400` `invalidDataTypeOfParameter`.
  - Missing permissions → `403` `insufficientRights`.

---

## Service Account Exclusions

**Enrollment Behavior for Service Accounts:**

Service accounts are automated systems that cannot perform 2FA (they're not humans). They are completely excluded from enrollment:

- **Never prompted** for TOTP enrollment (no `shouldPromptTotpEnrollment` flag)
- **Never required** to set up TOTP (no `requireTotpSetup` flag, even in mandatory roles)
- Use IP whitelist security instead of 2FA

**Database Flag:**
```sql
SELECT is_service_account FROM users WHERE "actorId" = ?
```
If `true`, skip ALL enrollment checks (mandatory and optional).

**Login Response for Service Account:**
```json
{
  "actorId": 42,
  "token": "WlHP4MlKyhIwowR6YhV7bQTG...",
  "expiresAt": "2026-02-09T08:32:29.843Z",
  "createdAt": "2026-02-08T08:32:29.848Z",
  "csrf": "AKOPikMi2RTj2v$Jg2j6yC...",
  "totp_verified": true
}
```
No enrollment flags, even if assigned to admin role.

---
