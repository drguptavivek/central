# TOTP 2FA API Contracts

## Overview

Two-phase login flow for users with TOTP (Time-based One-Time Password) 2FA enabled.

## Login Flow

```
User → [Phase 1: Password] → [Phase 2: TOTP Code] → Logged In
```

## API Endpoints

### Phase 1: POST /v1/sessions (Email/Password Login)

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response (No TOTP Required):** - HTTP 200
```json
{
  "actorId": 5,
  "token": "session_token_here",
  "expiresAt": "2026-02-09T08:02:50.466Z",
  "createdAt": "2026-02-08T08:02:50.466Z",
  "csrf": "csrf_token_here",
  "totp_verified": true  // ← User is fully authenticated
}
```
**Frontend Action:** Store session, proceed to app

---

**Response (TOTP Required):** - HTTP 200
```json
{
  "actorId": 5,
  "token": "temp_session_token_here",
  "expiresAt": "2026-02-09T08:02:50.466Z",
  "createdAt": "2026-02-08T08:02:50.466Z",
  "csrf": "csrf_token_here",
  "totp_verified": false,  // ← TOTP verification required
  "requireTotp": true      // ← Signal that TOTP is needed
}
```
**Frontend Action:**
- Store the session temporarily
- Show TOTP entry screen
- Do NOT proceed to app

**Error Responses:**
- `401.2` (HTTP 401): Invalid credentials
- `429.1` (HTTP 429): Too many login attempts

---

### Phase 2: POST /v1/sessions/totp-verify (TOTP Code Verification)

**Requires:** Active session with `totp_verified: false` (from Phase 1)

**Request:**
```json
{
  "token": "123456"  // 6-digit TOTP code from authenticator app
}
```

OR (for backup codes):
```json
{
  "token": "BACKUP-CODE-HERE"  // 8-character backup code
}
```

**Response:** - HTTP 200
```json
{
  "ok": true  // Session marked as verified
}
```
**Frontend Action:**
- Session is now `totp_verified: true`
- Proceed to app
- Fetch current user data

**Error Responses:**
- `401.7` (HTTP 401): Invalid TOTP code
- `429.1` (HTTP 429): Too many verification attempts

---

### Session Restoration: GET /v1/sessions/restore

**Requires:** Valid session cookie

**Response:** - HTTP 200
```json
{
  "createdAt": "2026-02-08T08:02:50.466Z",
  "expiresAt": "2026-02-09T08:02:50.466Z",
  "totp_verified": true  // ← Check this!
}
```

**If `totp_verified: false`:**
- Session exists but TOTP verification incomplete
- Frontend must clear session and redirect to login
- User must complete TOTP verification before accessing app

---

## Key Rules for Frontend Implementation

### 1. **Phase 1 Response Handling**

```javascript
POST /v1/sessions → Check response.totp_verified:
  ├─ true → User fully authenticated
  │         Store session and proceed
  └─ false → User needs TOTP
            Store session temporarily
            Show TOTP entry screen
```

### 2. **Phase 2 Before App Access**

- User MUST enter TOTP code
- POST /v1/sessions/totp-verify must complete successfully
- Only after success, proceed to app

### 3. **Page Reload Protection**

```javascript
On page reload:
  GET /v1/sessions/restore

  If response.totp_verified === false:
    ├─ Clear session data
    ├─ Remove from localStorage
    └─ Redirect to login (TOTP incomplete)

  If response.totp_verified === true:
    └─ Proceed normally
```

### 4. **TOTP Entry UI**

Only show TOTP input after:
- Phase 1 response received with `requireTotp: true`
- Response contains valid session token
- Session cookie is set by browser

### 5. **Error Handling**

```javascript
POST /v1/sessions → 401.2 error:
  └─ Show: "Invalid email or password"

POST /v1/sessions/totp-verify → 401.7 error:
  └─ Show: "Invalid TOTP code"

POST /v1/sessions/totp-verify → 429.1 error:
  └─ Show: "Too many attempts, please try again later"
```

---

## Security Requirements

1. **HTTP-Only Cookies:** Session token is always sent via HTTP-only cookie
   - Frontend cannot access token from JavaScript
   - Automatic with all requests after Phase 1

2. **CSRF Protection:** CSRF token provided in response
   - Include in POST requests as required

3. **Timeout Protection:**
   - Phase 1 response token expires after timeout
   - Phase 2 must complete before timeout
   - If timeout, user must login again

4. **Rate Limiting:**
   - Phase 1: 5 failures per 5 minutes from same IP
   - Phase 2: Similar limits apply
   - Lockout headers in response: `X-Login-Attempts-Remaining`, `Retry-After`

---

## Example Frontend Flow

```javascript
// Phase 1: Get password from user, submit login
const loginResponse = await POST('/v1/sessions', {
  email: userEmail,
  password: userPassword
});

if (loginResponse.totp_verified === true) {
  // User logged in fully, proceed to app
  navigateToApp();
} else if (loginResponse.requireTotp === true) {
  // Show TOTP entry screen
  showTotpInput();
}

// Phase 2: Get TOTP code from user, verify
const totpCode = await getUserTotpCode();  // User enters 6 digits
const verifyResponse = await POST('/v1/sessions/totp-verify', {
  token: totpCode
});

if (verifyResponse.ok === true) {
  // TOTP verified successfully
  // Session is now fully authenticated
  navigateToApp();
}

// On page reload
const restoreResponse = await GET('/v1/sessions/restore');
if (restoreResponse.totp_verified === false) {
  // Clear session and redirect to login
  clearSession();
  redirectToLogin();
} else {
  // Continue normally
  proceedToApp();
}
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Can access app without TOTP after refresh | Session data not cleared | Frontend must clear session when `totp_verified: false` |
| TOTP screen never appears | `requireTotp` flag not checked | Check response object for `requireTotp: true` |
| Cannot verify TOTP | Invalid code | Ensure 6-digit code from app, retry |
| 401 error on TOTP verify | Session expired | Restart login from Phase 1 |
| Lost access to authenticator app | Can use backup codes | 8-character codes work as TOTP replacement |

