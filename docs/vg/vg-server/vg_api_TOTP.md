# TOTP 2FA Server API Documentation

**Last Updated:** 2026-02-08
**Status:** ✅ Production Ready

---

## Overview

Two-Factor Authentication (2FA) using Time-based One-Time Passwords (TOTP). Server-side implementation handles:
- TOTP secret generation and storage
- QR code generation for authenticator apps
- TOTP code verification
- Backup codes generation and validation
- Session verification state management

---

## Architecture

### Database Tables

**`vg_web_user_totp`** - User TOTP Configuration
```sql
CREATE TABLE vg_web_user_totp (
  id SERIAL PRIMARY KEY,
  actor_id INTEGER NOT NULL UNIQUE REFERENCES actors(id),
  totp_secret VARCHAR(255) NOT NULL,      -- Base32 encoded secret
  totp_enabled BOOLEAN DEFAULT false,      -- Whether 2FA is active
  totp_enabled_at TIMESTAMP,                -- When 2FA was enabled
  backup_codes TEXT,                        -- JSON array of backup codes
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

**`sessions`** - Extended with TOTP verification state
```sql
ALTER TABLE sessions ADD COLUMN totp_verified BOOLEAN DEFAULT true;
-- true = fully authenticated
-- false = password verified but TOTP pending
```

---

## API Endpoints

### 1. Setup TOTP (Begin Enrollment)

**Endpoint:** `POST /v1/users/:id/totp/setup`

**Authentication:** Required (user can setup their own, admin can setup others)

**Response:** HTTP 200
```json
{
  "secret": "JBSWY3DPEBLW64TMMQ======",        // Base32 encoded secret
  "qrCode": "data:image/png;base64,...",       // QR code data URL
  "backupCodes": [
    "BACKUP-0001",
    "BACKUP-0002",
    ...
    "BACKUP-0010"
  ]
}
```

**Implementation Details:**
- Generates random 32-byte secret
- Encodes as Base32 (RFC 4648)
- Creates TOTP provisioning URI: `otpauth://totp/ODK%20Central?secret=JBSWY3DPEBLW64TMMQ%3D%3D%3D%3D%3D%3D&issuer=ODK%20Central`
- Generates QR code as PNG data URL
- Creates 10 backup codes (8 characters each, alphanumeric)
- Does NOT save to database yet (temporary setup state)

---

### 2. Enable TOTP (Verify First Code)

**Endpoint:** `POST /v1/users/:id/totp/enable`

**Authentication:** Required

**Request Body:**
```json
{
  "token": "123456"  // 6-digit code from authenticator app
}
```

**Response:** HTTP 200
```json
{
  "ok": true
}
```

**Implementation Details:**
- Validates 6-digit TOTP code against secret from setup request
- If valid:
  - Saves secret to `vg_web_user_totp` table
  - Marks `totp_enabled = true`
  - Sets `totp_enabled_at = NOW()`
  - Saves encrypted backup codes
  - Updates audit log: `vg.totp.enabled`
- If invalid:
  - Returns error 401.7 (Invalid code)
  - No state changes

---

### 3. Disable TOTP

**Endpoint:** `POST /v1/users/:id/totp/disable`

**Authentication:** Required + Password verification

**Request Body:**
```json
{
  "password": "userPassword"
}
```

**Response:** HTTP 200
```json
{
  "ok": true
}
```

**Implementation Details:**
- Verifies user's password (prevent unauthorized disable)
- If valid:
  - Marks `totp_enabled = false` (keeps historical record)
  - Clears `backup_codes`
  - Updates audit log: `vg.totp.disabled`
- If invalid:
  - Returns error 401.2 (Incorrect password)

---

### 4. Regenerate Backup Codes

**Endpoint:** `POST /v1/users/:id/totp/backup-codes/regenerate`

**Authentication:** Required + Password verification

**Request Body:**
```json
{
  "password": "userPassword"
}
```

**Response:** HTTP 200
```json
{
  "backupCodes": [
    "BACKUP-0001",
    "BACKUP-0002",
    ...
    "BACKUP-0010"
  ]
}
```

**Implementation Details:**
- Verifies user's password
- Generates 10 new backup codes
- Saves encrypted to database (invalidates old codes)
- Updates audit log: `vg.totp.backup_codes_regenerated`

---

### 5. Get TOTP Status

**Endpoint:** `GET /v1/users/:id/totp/status`

**Authentication:** Required

**Response:** HTTP 200
```json
{
  "enabled": true,
  "enabledAt": "2026-01-15T10:30:00Z"
}
```

---

## Login Flow - Server-Side

### Phase 1: POST /v1/sessions (Email + Password)

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Flow:**
1. Verify email and password
2. Check if user has TOTP enabled:
   ```sql
   SELECT totp_enabled FROM vg_web_user_totp WHERE actor_id = ?
   ```

**Response A** (No TOTP):
```json
{
  "actorId": 5,
  "token": "...",
  "expiresAt": "...",
  "totp_verified": true
}
// Session is fully authenticated, cookie is set
```

**Response B** (TOTP Required):
```json
{
  "actorId": 5,
  "token": "WlHP4MlKyhIwowR6YhV7bQTG9KgcMxPBT2JkL8JsFe2YB!lDy9xtEi!yKLf6JQP9",
  "expiresAt": "2026-02-08T08:33:29.843Z",  // 60 seconds from now
  "createdAt": "2026-02-08T08:32:29.848Z",
  "csrf": "AKOPikMi2RTj2v$Jg2j6yC$u6uvmi9$k2yOhS2OR1CcCgdqqv!0AOKYWZ!IsSjHc",
  "totp_verified": false,
  "requireTotp": true
}
// Session created in database but marked unverified
// ⚠️ COOKIES ARE NOT SET (security: prevents bypass via page refresh)
// Token returned in response body for Bearer authentication
// Token expires in 60 seconds - user must complete TOTP quickly
// Frontend must send token as Bearer header in Phase 2
```

**Security Note:** Cookies are intentionally NOT set in Phase 1. This prevents users from bypassing TOTP by refreshing the page. The session token is only valid for the `/sessions/totp-verify` endpoint.

**Code Location:** `/server/lib/resources/sessions.js:127-148`

---

### Phase 2: POST /v1/sessions/totp-verify (TOTP Code)

**Authentication:** Bearer token (from Phase 1 response)

**Request Headers:**
```
Authorization: Bearer WlHP4MlKyhIwowR6YhV7bQTG9KgcMxPBT2JkL8JsFe2YB!lDy9xtEi!yKLf6JQP9
```

**Request Body:**
```json
{
  "token": "123456"  // 6-digit TOTP or 8-char backup code
}
```

**Response:** HTTP 200
```json
{
  "token": "WlHP4MlKyhIwowR6YhV7bQTG9KgcMxPBT2JkL8JsFe2YB!lDy9xtEi!yKLf6JQP9",
  "csrf": "cfktRm90a5NZN0j4SEcOnSF8S3ssJbBZBye3w9iJLINNF3kHrrnEYMEyN!3hRqYA",
  "expiresAt": "2026-02-09T08:43:10.889Z",  // Extended to full session duration
  "createdAt": "2026-02-08T04:49:24.263Z",
  "id": 5,
  "type": "user",
  "displayName": "drguptavivek@yahoo.com"
}
// Cookies are NOW set (HttpOnly, Secure, SameSite=Strict)
// Session is fully authenticated
// Frontend can proceed with login
```

**Flow:**
1. Verify Bearer token from Authorization header
2. Get session from database using token
3. Verify session exists and `totp_verified = false`
4. Get TOTP secret from database:
   ```sql
   SELECT totp_secret FROM vg_web_user_totp WHERE actor_id = ?
   ```
5. Validate TOTP code:
   - Generate expected codes for current time window ± 1 step
   - Accept if matches (prevents clock skew)
6. If invalid, check backup codes:
   - Match against encrypted backup codes
   - Mark as used (single-use only)
7. On success:
   - Update session: `totp_verified = true`
   - **Extend expiration** to full `sessionLifetime` (was 60s, now ~24h)
   - **Set session cookies** (HttpOnly, Secure, SameSite=Strict)
   - **Set CSRF cookie**
   - Return updated session data to frontend
   - Log audit: `vg.totp.verified`
8. On failure:
   - Return error 401.7
   - Log attempt

**Code Location:** `/server/lib/resources/vg-web-user-totp.js:118-165`

---

## Session Management

### Session Creation with TOTP State

**File:** `/server/lib/resources/sessions.js`

**For users WITHOUT TOTP:**
```javascript
// Standard session creation with cookies
createUserSession({ Audits, Sessions, Users }, headers, user, true)
  .then((middleware) => middleware(_, response));
  // totpVerified: true = fully authenticated
  // Cookies are set immediately
  // Session expires per config.default.sessionLifetime
```

**For users WITH TOTP:**
```javascript
// Two-phase session creation WITHOUT cookies in Phase 1
const totpSessionExpiry = new Date(Date.now() + 60 * 1000);  // 60 seconds
Promise.all([
  Sessions.create(user.actor, totpSessionExpiry, false),  // totp_verified=false
  Audits.log(user.actor, 'user.session.create', user.actor, { userAgent }),
  Users.updateLastLoginAt(user)
])
  .then(([ session ]) => {
    // Return session WITHOUT executing cookie middleware
    return { ...session, requireTotp: true };
  });

// Phase 2 (after TOTP verification):
// - markTotpVerified() sets totp_verified=true and extends expiration
// - Cookies are set in totp-verify endpoint response
```

**Key Differences:**
- **No TOTP**: Cookies set immediately, session lasts full duration
- **TOTP Phase 1**: No cookies, session expires in 60s, token in response body
- **TOTP Phase 2**: Cookies set after verification, session extended to full duration

### TOTP Verification Check (Middleware)

**File:** `/server/lib/http/preprocessors.js:40-66`

All requests are checked for TOTP verification:

```javascript
// Skip TOTP check for certain endpoints
const skipTotpPaths = [
  /\/users\/[^\/]+\/totp\/setup/,      // Setup (no verification yet)
  /\/users\/[^\/]+\/totp\/enable/,     // Enable (verification in progress)
  /\/users\/[^\/]+\/totp\/disable/,    // Disable (user action)
  /\/sessions\/totp-verify/             // TOTP verification itself
];

// For other endpoints:
if (session.totp_verified === false && userHasTotpEnabled) {
  throw Problem.user.insufficientRights();  // 403 Forbidden
}
```

**Protection:**
- Users with TOTP enabled cannot access other endpoints until `totp_verified = true`
- Prevents accessing API/UI without completing TOTP
- Exception: `/sessions/totp-verify` endpoint to complete verification

---

## TOTP Code Validation

### Algorithm: HOTP (RFC 4226) + Time Windows (RFC 6238)

**Code Verification:** `/server/lib/domain/vg-totp.js`

```javascript
function verifyTotpCode(secret, code, window = 1) {
  const now = Math.floor(Date.now() / 1000);
  const timeStep = 30;  // Standard 30-second window

  // Check current and adjacent time windows
  for (let i = -window; i <= window; i++) {
    const counter = Math.floor(now / timeStep) + i;
    const expectedCode = generateHotp(secret, counter);
    if (expectedCode === code) {
      return true;
    }
  }
  return false;
}
```

**Features:**
- 6-digit codes
- 30-second validity window
- ±1 step tolerance (prevents edge-case timing issues)
- Constant-time comparison (prevents timing attacks)

---

## Error Codes

| Code | HTTP | Meaning | Action |
|------|------|---------|--------|
| `401.7` | 401 | Invalid TOTP code | Retry with correct code |
| `401.2` | 401 | Password incorrect | Retry password |
| `400.13` | 400 | Backup code already used | Use different code |
| `429.1` | 429 | Too many attempts | Wait before retrying |
| `403` | 403 | TOTP required but not verified | Complete TOTP |

---

## Audit Logging

All TOTP actions are logged to `audits` table:

```sql
-- 2FA Setup
INSERT INTO audits (actor_id, action, details)
VALUES (?, 'vg.totp.setup_initiated', {secret: '***'});

-- 2FA Enabled
INSERT INTO audits (actor_id, action, details)
VALUES (?, 'vg.totp.enabled', {user: 'admin@example.com'});

-- TOTP Verified (during login)
INSERT INTO audits (actor_id, action, details)
VALUES (?, 'vg.totp.verified', {ip: '192.168.1.100'});

-- 2FA Disabled
INSERT INTO audits (actor_id, action, details)
VALUES (?, 'vg.totp.disabled', {user: 'admin@example.com'});

-- Backup Codes Regenerated
INSERT INTO audits (actor_id, action, details)
VALUES (?, 'vg.totp.backup_codes_regenerated', {});
```

---

## Dependencies

### NPM Packages
- `speakeasy` - TOTP generation and verification
- `qrcode` - QR code generation
- `base32.js` - Base32 encoding/decoding

### System Requirements
- Node.js 22+
- PostgreSQL 14+

---

## Testing

### Unit Tests

**Location:** `/server/test/unit/util/vg-totp.js`

```bash
npm test -- test/unit/util/vg-totp.js
```

Tests:
- Code generation accuracy
- Code validation (current + ±1 window)
- Backup code validation
- Error cases (invalid codes, expired codes)

### Integration Tests

**Location:** `/server/test/integration/api/vg-web-user-totp.js`

```bash
npm test -- test/integration/api/vg-web-user-totp.js
```

Tests:
- Full TOTP setup flow
- Login with TOTP
- Backup code usage
- Session verification state
- Error handling

---

## Security Considerations

### 1. **Secret Storage**
- Secrets are encrypted in database
- Never logged or exposed in responses
- Only transmitted during setup QR code

### 2. **Code Validation**
- Constant-time comparison (prevents timing attacks)
- ±1 window tolerance (prevents clock skew issues)
- Single-use backup codes (each code marked used)

### 3. **Session State & Two-Phase Login**
- `totp_verified` state prevents API access until 2FA complete
- Middleware enforces check on all requests
- **Phase 1 (password):** No cookies set, token in response body only
  - Prevents page refresh bypass attack
  - Token stored in memory (frontend), not cookies
  - If user refreshes page, token is lost and login must restart
- **Phase 2 (TOTP):** Cookies set only after successful verification
  - Session becomes fully functional only after TOTP
  - Page refresh after TOTP completion keeps user logged in (correct behavior)
- **60-second expiration** for unverified sessions forces quick TOTP entry
- Session extended to full `sessionLifetime` after TOTP verification

### 4. **Rate Limiting**
- 5 failed TOTP attempts per 5 minutes per IP
- 10-minute lockout after threshold
- Same limits as password login

### 5. **Backup Codes**
- 8-character alphanumeric (high entropy)
- Single-use only (marked in database)
- Encrypted at rest
- Limited to 10 codes per user

### 6. **Bearer Token Authentication (Phase 1 → Phase 2)**
- Phase 1 session token returned in response body, not in cookies
- Frontend sends token as `Authorization: Bearer <token>` header in Phase 2
- Token only valid for `/sessions/totp-verify` endpoint
- Middleware blocks all other endpoints when `totp_verified=false`
- Token expires in 60 seconds, forcing timely TOTP completion
- After verification, Bearer token becomes cookie-based session token

**Endpoint Whitelist for Unverified Sessions:**
- `/users/:id/totp/setup`
- `/users/:id/totp/enable`
- `/users/:id/totp/disable`
- `/users/:id/totp/backup-codes/*`
- `/users/:id/totp/status`
- `/sessions/totp-verify` ← **Critical for Phase 2**

All other endpoints return `403 Forbidden` when `totp_verified=false`.

---

## Configuration

**Environment Variables:**
```bash
TOTP_WINDOW=1              # Time window tolerance (±1 step)
TOTP_STEP=30               # Seconds per time step (RFC 6238 standard)
TOTP_DIGITS=6              # Code length in digits
TOTP_ALGORITHM=SHA1        # Hash algorithm (SHA1 standard)
```

---

## Related Documentation

- [TOTP API Contracts (Client-facing)](../vg-client/TOTP_API_CONTRACTS.md)
- [TOTP Client Implementation](../vg-client/totp-client.md)
- [IP Whitelist Admin Guide](vg_ip_whitelist_admin_guide.md)
- [Web User Login Hardening](web-user-lockout-implementation.md)

