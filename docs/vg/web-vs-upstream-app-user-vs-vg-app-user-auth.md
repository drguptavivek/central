# Web Users vs App Users: Authentication & Endpoint Access Comparison

> **TL;DR**: ODK Central has two main actor types with **completely different access levels**.

## Critical Distinction: Actor Types & Endpoint Access

| Actor Type | User Type | Endpoint Access | Auth Method | TOTP Check |
|------------|-----------|----------------|-------------|------------|
| **`user`** | Web Users (Interactive) | **ALL endpoints** | Cookie | ✅ Enforced |
| **`user`** | Web Users (Service) | **ALL endpoints** | Bearer header | ❌ Bypassed |
| **`field_key`** | App Users | **OpenRosa ONLY** | URL: `/key/{token}/...` | ❌ N/A |

**Key Insight:** Web user bearer tokens **bypass TOTP** checks. TOTP only applies to cookie-based web UI login, not programmatic API access.

---

## Web User Tokens (Actor Type: `user`)

### Two Distinct Use Cases

#### 1. Interactive Web Users (Cookie-based)
**Purpose:** Human administrators using the web UI

**What They Can Access: EVERYTHING**

**Full REST API Access:**
```bash
# Projects & Forms
GET /v1/projects
POST /v1/projects
GET /v1/projects/:id/forms
POST /v1/projects/:id/forms

# Users & Roles
GET /v1/users
POST /v1/users
PATCH /v1/users/:id
GET /v1/assignments

# Submissions (REST API)
GET /v1/projects/:id/forms/:fid/submissions
GET /v1/projects/:id/forms/:fid/submissions.csv
GET /v1/projects/:id/forms/:fid/submissions/:sid

# App Users Management
GET /v1/projects/:id/app-users
POST /v1/projects/:id/app-users
POST /v1/projects/:id/app-users/:uid/password/reset

# System Settings
GET /v1/config/backups
POST /v1/config/backups
```

**OpenRosa API (can also access):**
```bash
GET /v1/projects/:id/formList
POST /v1/projects/:id/submission
```

### Authentication Methods

**Cookie-based (Web UI):**
```bash
Cookie: __Host-session=abc123...
# Used by Central Frontend
```

**Bearer Token (Programmatic):**
```bash
Authorization: Bearer abc123...
# Used for web UI and can also be used for API automation
```

### Token Characteristics
- **Lifetime**: 24 hours (default, configurable)
- **TOTP**: Optional 2FA (enforced for cookie auth only)
- **Rate Limiting**: 5 failures per email+IP → 10-minute lockout
- **Scope**: System-wide (can access all projects they have permission for)

---

#### 2. Service Users (Bearer Token-based)
**Purpose:** Programmatic API access, automation scripts, integrations

**Critical Discovery:** Bearer tokens **bypass TOTP checks entirely**!

**Code Evidence** (`server/lib/http/preprocessors.js:99-109`):
```javascript
const authBySessionToken = (token, isCookie = false) => {
  return Sessions.getByBearerToken(token)
    .then((cxt) => {
      if (isCookie) {
        return checkTotpVerification(...);  // ← Only for cookies!
      }
      return checkIpWhitelist(...);  // ← Bearer tokens skip TOTP!
    });
}
```

**What Service Users Can Do:**
```bash
# Full REST API access (same as interactive web users)
curl -H "Authorization: Bearer {token}" https://central.local/v1/projects
curl -H "Authorization: Bearer {token}" https://central.local/v1/users
curl -H "Authorization: Bearer {token}" https://central.local/v1/projects/1/forms
curl -H "Authorization: Bearer {token}" https://central.local/v1/projects/1/submissions.csv

# Even if the user has TOTP enabled!
# Bearer tokens bypass TOTP verification
```

**How to Create a Service User:**
1. Create web user account via web UI
2. Assign appropriate role (viewer, project manager, admin)
3. Login via API to get bearer token:
   ```bash
   curl -X POST https://central.local/v1/sessions \
     -H "Content-Type: application/json" \
     -d '{"email":"service@example.com","password":"SecurePass!123"}'

   # Returns: { "token": "abc123...", "expiresAt": "..." }
   ```
4. Use bearer token for all API requests
5. Token expires after 24 hours → re-login

**Security Considerations:**
- **TOTP is NOT checked** for bearer tokens (by design)
- **IP Whitelist CAN be enforced** (VG feature)
- Recommended: Create dedicated service accounts with minimal permissions
- Recommended: Enable IP whitelist for service accounts
- **Not recommended**: Use admin accounts for service users (too much privilege)

**VG Design:**
- **Cookie auth** (web UI) → TOTP enforced → humans only
- **Bearer token auth** (API) → TOTP bypassed → allows automation
- This separation enables programmatic access while securing interactive login

---

## App User Tokens: Upstream vs VG

> **Key Insight**: App user tokens (actor type `field_key`) can **ONLY access OpenRosa endpoints** (formList, submission, manifest). They CANNOT access REST API endpoints (/projects, /users, etc.). This is true for BOTH upstream QR tokens and VG password tokens.

---

## The Surprising Truth

**Both use the exact same token validation system:**
- Same 64-character alphanumeric token format
- Same `Sessions.getByBearerToken()` validation function
- Same `sessions` table storage
- Same token generation algorithm
- Same URL-based authentication: `/key/{token}/...` or `?st={token}`
- Same actor type: `field_key`
- Same endpoint access: OpenRosa only

**What's different:**
- How the token is obtained
- How long it lasts
- User onboarding experience
- Re-authentication requirements

---

## Side-by-Side Comparison

| Aspect | Upstream App User Token | VG Password App User Token |
|--------|------------------------|---------------------------|
| **Token Format** | 64-char alphanumeric | 64-char alphanumeric (SAME) |
| **Storage** | `sessions` table | `sessions` table (SAME) |
| **Validation** | `Sessions.getByBearerToken()` | `Sessions.getByBearerToken()` (SAME) |
| **Actor Type** | `field_key` | `field_key` (SAME) |
| **Token Obtaining** | Admin creates app user → QR code | User logs in with username/password |
| **Creation Endpoint** | `POST /v1/projects/:id/app-users` (admin) | `POST /v1/projects/:id/app-users/login` (user) |
| **Token Lifetime** | **~1000 years** (permanent) | **3 days** (default, configurable) |
| **Token Delivery** | URL: `/key/{token}/...` or `?st={token}` | URL: `/key/{token}/...` or `?st={token}` (SAME) |
| **Initial Setup** | Scan QR code (one-time) | Enter username/password |
| **Re-authentication** | Never (token permanent) | Every 3 days (on token expiry) |
| **Error Response** | 403 Forbidden | 403 Forbidden (SAME) |
| **Use Case (Upstream)** | ODK Collect form sync | Not available |
| **Use Case (VG Fork)** | Still works | **Primary method** (easier UX) |
| **Session Cap** | None | 3 sessions (default, configurable) |
| **Revocation** | Delete app user or revoke session | Explicit revoke, expiry, or logout |
| **Endpoint Access** | OpenRosa only | OpenRosa only (SAME) |

---

## How They Work Under the Hood

### Upstream App User Token Flow (ODK Central)

```
1. Admin creates app user via web UI
   POST /v1/projects/1/app-users
   ↓
2. Server generates 64-char token, stores in sessions table
   ↓
3. Token displayed as QR code (1000-year expiry)
   ↓
4. User scans QR code into ODK Collect (one-time setup)
   ↓
5. ODK Collect makes requests with token in URL:
   GET /v1/key/ABC123...XYZ/projects/1/formList
   ↓
6. Server extracts token from URL, calls Sessions.getByBearerToken()
   ↓
7. Validates: token exists, not expired, actor type = field_key
   ↓
8. Request authenticated ✅
```

**Key characteristics:**
- **QR code setup** - scan once, works forever
- **No password** - no user credentials needed
- **Permanent token** - ~1000 year expiry
- **Token in URL** - `/key/{token}/...` or `?st={token}`
- **Upstream default** - ODK Central's original design
- **One-time setup** - never need to re-authenticate

### VG Password App User Token Flow (VG Fork)

```
1. Admin creates app user with username/password via web UI
   ↓
2. User logs in with username/password from mobile app
   POST /v1/projects/1/app-users/login
   { "username": "collector", "password": "Pass!123" }
   ↓
3. Server validates password, generates 64-char token
   ↓
4. Token stored in sessions table with 3-day expiry
   ↓
5. Token returned in response: { "token": "ABC123...XYZ", "expiresAt": "..." }
   ↓
6. App stores token, makes requests with token in URL:
   GET /v1/key/ABC123...XYZ/projects/1/formList
   ↓
7. Server extracts token from URL, calls Sessions.getByBearerToken()
   ↓
8. Validates: token exists, not expired, actor type = field_key
   ↓
9. Request authenticated ✅
```

**Key characteristics:**
- **Password login** - username/password like any app
- **Short-lived** - expires after 3 days (configurable)
- **Token in URL** - same format as upstream: `/key/{token}/...`
- **Periodic re-login** - user logs in every 3 days
- **VG innovation** - easier UX, no QR codes
- **Same authentication** - uses same URL format as upstream

---

## The Shared Token Validation Code

**From `server/lib/http/preprocessors.js`:**

```javascript
// Field Key authentication (URL-based)
if (context.fieldKey.isDefined()) {
  const key = context.fieldKey.get();  // Extract from URL
  return Sessions.getByBearerToken(key)  // ← SAME FUNCTION
    .then((session) => {
      // Must be field_key or public_link
      if (session.actor.type !== 'field_key' && session.actor.type !== 'public_link')
        return reject(Problem.user.insufficientRights());
      return context.with({ auth: Auth.by(session) });
    });
}

// Bearer Token authentication (Header-based)
else if (authHeader.startsWith('Bearer ')) {
  const token = authHeader.substring(7);
  return Sessions.getByBearerToken(token)  // ← SAME FUNCTION
    .then((session) => context.with({ auth: Auth.by(session) }));
}
```

**Both call the same validation:**
```javascript
Sessions.getByBearerToken(token)
  // Queries sessions table
  // Checks expiration
  // Validates actor active status
  // Returns session object
```

---

## Token Format

**Both use:**
```javascript
// From server/lib/util/crypto.js
function generateToken() {
  return randomBytes(48).toString('base64')
    .replace(/\+/g, '!')
    .replace(/\//g, '$')
    .replace(/=/g, '')
    .substring(0, 64);
}

// Validation regex
/^[A-Za-z0-9!$]{64}$/
```

**Example tokens (both formats look identical):**
```
Field Key:     ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!$
App User Token: XYZ987654321abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUV!$
```

You cannot tell them apart by looking at the token string!

---

## Database Schema

**Both stored in the same table:**

```sql
-- sessions table (from upstream ODK)
CREATE TABLE sessions (
  "actorId" INTEGER NOT NULL,
  token VARCHAR(64) NOT NULL UNIQUE,
  "expiresAt" TIMESTAMP,  -- Field keys: NULL or far future
                          -- App tokens: NOW() + 3 days
  csrf VARCHAR(64),
  totp_verified BOOLEAN DEFAULT true,
  "createdAt" TIMESTAMP DEFAULT NOW()
);

-- field_keys table (links to sessions)
CREATE TABLE field_keys (
  "actorId" INTEGER PRIMARY KEY,  -- FK to actors.id
  "projectId" INTEGER,
  public TEXT,  -- Optional: RSA public key (advanced feature, rarely used)
  ...
);

-- vg_field_key_auth table (VG addition for passwords)
CREATE TABLE vg_field_key_auth (
  "actorId" INTEGER PRIMARY KEY,  -- FK to field_keys.actorId
  vg_username VARCHAR(255),
  vg_password_hash TEXT,  -- bcrypt hash
  vg_active BOOLEAN DEFAULT true,
  ...
);
```

**Token lookup (same for both):**
```sql
SELECT sessions.*, actors.*
FROM sessions
JOIN actors ON actors.id = sessions."actorId"
WHERE sessions.token = 'ABC123...XYZ'
  AND sessions."expiresAt" > NOW()  -- Field keys may have NULL here
```

---

## Why VG Fork Added Password Tokens

### Upstream ODK (QR Code Tokens)

**Pros:**
- ✅ One-time setup (scan QR code)
- ✅ No password to remember
- ✅ Permanent (no re-authentication)
- ✅ Simple for field workers (just scan)

**Cons:**
- ❌ Requires physical access to admin's screen (QR code)
- ❌ Token can't be shared verbally/remotely
- ❌ If token lost, admin must create new app user
- ❌ No user self-service (admin dependent)
- ❌ Permanent token = higher risk if compromised
- ❌ No device/session tracking

### VG Fork (Password-Based Tokens)

**Pros:**
- ✅ Remote onboarding (username/password over phone/email)
- ✅ User self-service (login anytime, anywhere)
- ✅ Password reset by admin
- ✅ Password change by user
- ✅ Short-lived tokens (reduced risk if compromised)
- ✅ Session management (cap, history, device tracking)
- ✅ User activation/deactivation
- ✅ Familiar authentication pattern

**Cons:**
- ❌ Passwords can be compromised
- ❌ Need to re-login every 3 days
- ❌ Adds password management complexity
- ❌ Users must remember credentials

---

## Coexistence in VG Fork

**Both methods work simultaneously:**

```
field_keys table:
┌─────────┬───────────┬────────────┐
│ actorId │ projectId │ public     │
├─────────┼───────────┼────────────┤
│   101   │     1     │ NULL       │  ← Upstream QR token user
│   102   │     1     │ NULL       │  ← VG password user
└─────────┴───────────┴────────────┘

vg_field_key_auth table (VG only):
┌─────────┬─────────────┬───────────────┐
│ actorId │ vg_username │ vg_password...│
├─────────┼─────────────┼───────────────┤
│   102   │ collector1  │ $2b$10$...   │  ← Password user only
└─────────┴─────────────┴───────────────┘

sessions table:
┌─────────┬────────────────┬────────────┐
│ actorId │ token          │ expiresAt  │
├─────────┼────────────────┼────────────┤
│   101   │ ABC123...      │ 2099-12-31 │  ← QR token (~1000 years)
│   102   │ XYZ789...      │ 2026-02-11 │  ← Password token (3 days)
└─────────┴────────────────┴────────────┘
```

**Identification:**
- If `vg_field_key_auth.actorId` exists → VG password user
- If NOT in `vg_field_key_auth` → Upstream QR token user
- Both are field_key actor type, both access OpenRosa only

---

## Token Delivery Comparison

### App User Tokens - URL Delivery (Both Upstream & VG)

```bash
# Query parameter (common)
GET /v1/projects/1/formList?st=ABC123...XYZ

# Path-based (deprecated)
GET /v1/key/ABC123...XYZ/projects/1/formList

# OpenROSA submission
POST /v1/projects/1/submission?st=ABC123...XYZ
```

**Security consideration:** Token appears in:
- Server access logs
- Proxy logs
- Browser history (if used in browser)

**Note:** While bearer header authentication (`Authorization: Bearer {token}`) technically works for app user tokens in the VG fork, Medres Collect uses the traditional URL-based format for compatibility with the OpenRosa protocol.

---

## Performance Comparison

| Operation | Upstream QR Token | VG Password Token |
|-----------|------------------|-------------------|
| **Token Generation** | One-time (at creation) | Every login (every 3 days) |
| **Token Validation** | Fast (DB lookup) | Fast (DB lookup) - SAME |
| **Authentication** | No password check | Bcrypt on login (slow) |
| **Session Management** | Minimal | Full (cap, expiry, device tracking) |

**Both validation speeds are identical** because they use the same `Sessions.getByBearerToken()` function.

---

## Migration Path

### Existing ODK Central (QR Tokens) → VG Fork

**Option 1: Dual Mode (Recommended)**
- Keep existing QR token app users working
- Create new users with passwords
- Gradually migrate as users re-register

**Option 2: Password-Only**
- Existing QR token app users continue to work (permanent tokens)
- New users must use passwords (short-lived tokens)

**Database changes:**
```sql
-- VG fork adds these tables
CREATE TABLE vg_field_key_auth (...);  -- Password storage
CREATE TABLE vg_settings (...);         -- Session TTL/cap config
CREATE TABLE vg_app_user_login_attempts (...);  -- Rate limiting

-- Upstream tables unchanged
-- field_keys, sessions, actors remain compatible
```

---

## Security Implications

### Upstream App User Token Strengths
- ✅ No password to compromise
- ✅ QR code makes token sharing visible
- ✅ Simple setup (less room for error)

### Upstream App User Token Weaknesses
- ⚠️ Token in URL (logging exposure)
- ⚠️ No expiration (permanent access if leaked)
- ⚠️ Difficult to rotate tokens
- ⚠️ Lost token = admin intervention required
- ⚠️ No session tracking (can't see active devices)

### VG Password Token Strengths
- ✅ Same URL format (no additional logging exposure)
- ✅ Auto-expiration (3 days) - limits damage if leaked
- ✅ Session cap limits concurrent access
- ✅ Easier to revoke/manage per device
- ✅ User can change password (self-service security)
- ✅ Session history (audit trail of logins)

### VG Password Token Weaknesses
- ⚠️ Password can be brute-forced (mitigated by rate limiting)
- ⚠️ Requires rate limiting on login
- ⚠️ Password complexity policy needed
- ⚠️ Users may write down passwords
- ⚠️ Token still in URL (same as upstream)

---

## Real-World Implementation: Medres Collect

**Medres Collect** (VG's ODK Collect fork) uses VG password tokens with traditional OpenRosa URL authentication:

```
User Experience:
1. Install Medres Collect app
2. Enter server URL, username, password
3. App calls: POST /v1/projects/1/app-users/login
4. Server returns: { "token": "ABC123...", "expiresAt": "2026-02-11..." }
5. App stores token

When syncing forms:
GET /v1/key/ABC123...XYZ/projects/1/formList

When submitting:
POST /v1/key/ABC123...XYZ/projects/1/submission

After 3 days:
- Token expires
- User re-enters username/password
- Gets new token (steps 3-5)
```

**Key advantages:**
- Remote onboarding (no physical QR code scanning)
- User can log in from anywhere
- Admin can reset passwords remotely
- Short-lived tokens reduce security risk

## Complete Comparison: All User Types

| Feature | Web User (Interactive) | Web User (Service) | Upstream App User | VG Password App User |
|---------|----------------------|-------------------|------------------|---------------------|
| **Actor Type** | `user` | `user` | `field_key` | `field_key` |
| **Token Obtaining** | Email/password login | Email/password login | QR code scan | Username/password login |
| **Token Format** | 64-char alphanumeric | 64-char alphanumeric | 64-char alphanumeric | 64-char alphanumeric |
| **Token Lifetime** | 24 hours | 24 hours | ~1000 years | 3 days |
| **Auth Method** | Cookie | Bearer header | URL: `/key/{token}/...` | URL: `/key/{token}/...` |
| **TOTP Check** | ✅ Enforced | ❌ **Bypassed** | ❌ N/A | ❌ N/A |
| **REST API Access** | ✅ Full access | ✅ Full access | ❌ Forbidden (403) | ❌ Forbidden (403) |
| **OpenRosa API** | ✅ Can access | ✅ Can access | ✅ Only access | ✅ Only access |
| **Create Projects** | ✅ (if admin) | ✅ (if admin) | ❌ | ❌ |
| **Manage Users** | ✅ (if admin) | ✅ (if admin) | ❌ | ❌ |
| **View Submissions (REST)** | ✅ | ✅ | ❌ | ❌ |
| **Submit Forms (OpenRosa)** | ✅ | ✅ | ✅ | ✅ |
| **Download Forms** | ✅ | ✅ | ✅ | ✅ |
| **Export CSV** | ✅ | ✅ | ❌ | ❌ |
| **System Settings** | ✅ (if admin) | ✅ (if admin) | ❌ | ❌ |
| **Programmatic Access** | ❌ Human only (TOTP) | ✅ **Yes** (TOTP bypassed) | ✅ Yes | ✅ Yes |
| **IP Whitelist** | N/A (cookies) | ✅ (VG, bearer only) | ❌ | ❌ |
| **Rate Limiting** | 5 failures/5min | 5 failures/5min | 5 failures/5min | 5 failures/5min |
| **Session Cap** | No | No | No | 3 (configurable) |
| **Use Case** | Web UI admin | API automation/scripts | ODK Collect (upstream) | Medres Collect (VG) |

---

## Summary: App Users Only (Not Web Users)

**App users (both upstream and VG) use the same token system:**

```
┌───────────────────────────────────────────────┐
│   App User Token Infrastructure (Identical)   │
│   • Actor type: field_key                     │
│   • 64-char tokens                            │
│   • sessions table                            │
│   • Sessions.getByBearerToken()               │
│   • URL authentication: /key/{token}/...      │
│   • OpenRosa endpoints only                   │
└───────────────────────────────────────────────┘
            ↓                    ↓
   ┌─────────────────┐   ┌─────────────────────┐
   │ QR Code Token   │   │ Password Token      │
   │ (Upstream)      │   │ (VG Fork)           │
   ├─────────────────┤   ├─────────────────────┤
   │ • QR code scan  │   │ • Username/password │
   │ • Permanent     │   │ • 3-day expiry      │
   │ • One-time setup│   │ • Periodic re-login │
   │ • Admin creates │   │ • User self-service │
   └─────────────────┘   └─────────────────────┘
     ODK Collect           Medres Collect
   (upstream fork)          (VG fork)
```

**Web users have two modes:**
- Actor type: `user` (not `field_key`)
- Full REST API access (not just OpenRosa)
- Cookie auth (TOTP enforced) OR Bearer header (TOTP bypassed)
- 24-hour sessions (not permanent or 3-day)

**Choose based on:**
- **Web Users (Interactive)** = Human admins using web UI
  - Cookie-based authentication
  - ✅ TOTP enforced for security
  - ❌ Cannot be used programmatically

- **Web Users (Service)** = API automation, scripts, integrations
  - Bearer token authentication
  - ❌ **TOTP bypassed** (critical discovery!)
  - ✅ Full programmatic access to REST API
  - Recommended: Use IP whitelist for security

- **Upstream App Users** = QR code tokens (one-time setup, permanent, OpenRosa only)
  - ✅ Can be used programmatically (no TOTP)
  - ❌ Limited to OpenRosa endpoints only

- **VG App Users** = Password tokens (remote onboarding, manageable, OpenRosa only)
  - ✅ Can be used programmatically (no TOTP)
  - ❌ Limited to OpenRosa endpoints only

**VG Security Model:**
- Interactive web login → TOTP enforced (cookie-based)
- Programmatic API access → TOTP bypassed (bearer token-based)
- This enables automation while securing human access

---

## References

- **Authentication Patterns:** `docs/vg/vg-server/routes/authentication-patterns.md`
- **App User Auth API:** `docs/vg/vg-server/routes/app-user-auth.md`
- **User Types Guide:** `docs/vg/vg-server/user-types-and-login-policies.md`
- **Code:** `server/lib/http/preprocessors.js` (lines 37-109)
