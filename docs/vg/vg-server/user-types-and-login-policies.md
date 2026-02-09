# ODK Central User Types and Login Policies

> **Last Updated**: 2026-02-09 (Added API Tokens + Service Accounts)

ODK Central has three distinct user types with different authentication mechanisms and access scopes.

---

## Overview

| User Type | Access Scope | Auth Method | Token Type | Use Case |
|-----------|-------------|-------------|------------|----------|
| **Web Users** | System-wide | Email/Password + Optional TOTP | Session Cookies + API Tokens | Web UI administration + programmatic access |
| **Web Users (Service Accounts)** | System-wide | Email/Password OR API Tokens | Bearer Tokens (1hr sessions, long-lived API tokens) | Automated systems (CI/CD, cron jobs) with mandatory IP whitelist |
| **App Users** | Project-scoped | Username/Password | Bearer Token (short-lived) | Mobile data collection (ODK Collect) |
| **Public Key Auth** | Project-scoped | RSA Public Key | Bearer Token (long-lived) | Programmatic API access |

### Key Changes (2026-02-09)
- ✅ **NEW: API Tokens** - Long-lived tokens for web users (created via TOTP-protected UI)
- ✅ **NEW: Service Accounts** - Web users marked for automation with mandatory IP whitelist
- ✅ **Enhanced IP Whitelist** - Service accounts require IP whitelist, regular users optional

---

## 1. Web Users (System Administrators)

### Purpose
System administrators and project managers who access the **web interface** for:
- Creating and managing projects
- Configuring forms
- Managing users
- Viewing submissions and analytics

### Authentication Method

#### **Standard Login (No 2FA)**
- **Endpoint**: `POST /v1/sessions`
- **Credentials**: Email + Password
- **Response**: Session cookies (HttpOnly, Secure, SameSite=Strict)
- **Token**: Bearer token included but cookies are primary auth mechanism
- **Expiration**: ~24 hours (configurable via `sessionLifetime`)

```json
POST /v1/sessions
{
  "email": "admin@example.com",
  "password": "SecurePass!123"
}

Response 200:
{
  "actorId": 5,
  "token": "WlHP4MlKy...",
  "expiresAt": "2026-02-09T08:32:29.843Z",
  "csrf": "AKOPikMi...",
  "totp_verified": true
}
```

#### **Two-Phase Login (TOTP 2FA Enabled)**

**Phase 1: Email + Password**
- Returns temporary 60-second token
- **No cookies set** (user not fully authenticated)
- Token only valid for `/sessions/totp-verify` endpoint

```json
POST /v1/sessions
{
  "email": "admin@example.com",
  "password": "SecurePass!123"
}

Response 200:
{
  "actorId": 5,
  "token": "WlHP4MlKy...",
  "expiresAt": "2026-02-08T08:33:29.843Z",  # 60s expiry
  "requireTotp": true,
  "totp_verified": false
}
```

**Phase 2: TOTP Verification**
- Submit 6-digit TOTP code or 12-digit backup code
- Uses Bearer token from Phase 1
- **Cookies now set** (user fully authenticated)
- Session expiration extended to full lifetime

```json
POST /v1/sessions/totp-verify
Authorization: Bearer WlHP4MlKy...
{
  "token": "123456"
}

Response 200:
{
  "token": "WlHP4MlKy...",
  "csrf": "cfktRm90a5...",
  "expiresAt": "2026-02-09T08:43:10.889Z",  # Full session lifetime
  ...user details...
}
```

#### **NEW: Enrollment Prompts (2FA Adoption)**

When users log in **without TOTP enabled**, the system checks enrollment policy:

**Mandatory Enforcement (Admin Role)**
- If user's role is in `vg_totp_mandatory_roles` setting (default: `["admin"]`)
- Login response includes: `requireTotpSetup: true, mandatory: true`
- **No cookies set** until TOTP is configured
- User must complete 2FA setup before accessing the system

**Optional Prompt (Other Roles)**
- If role is not mandatory, normal session created
- Response includes: `shouldPromptTotpEnrollment: true/false`
- Prompt can be dismissed (permanently or "remind me in X days")
- Cookies are set, user can access system normally

```json
# Admin without TOTP (mandatory)
POST /v1/sessions
Response 200:
{
  "token": "temp-token...",
  "expiresAt": "2026-02-08T08:37:29.843Z",  # 5 min temp session
  "requireTotpSetup": true,
  "mandatory": true
}

# Viewer without TOTP (optional)
POST /v1/sessions
Response 200:
{
  "token": "WlHP4MlKy...",
  "expiresAt": "2026-02-09T08:32:29.843Z",
  "shouldPromptTotpEnrollment": true,
  ...cookies set...
}
```

### Security Features
- **Rate Limiting**: 5 failed attempts per email+IP in 5 minutes → 10-minute lockout
- **IP Tracking**: Login attempts tracked per IP to prevent brute force
- **Audit Logging**: All login attempts (success/failure) logged with IP and user-agent
- **TOTP Rate Limiting**: 5 failed TOTP codes in 5 minutes → 10-minute lockout

### Password Policy
- Minimum 10 characters, maximum 72
- Must include: uppercase, lowercase, digit, special character (`~!@#$%^&*()_+-=,.`)

---

## 1b. Web Users: API Tokens (NEW - 2026-02-09)

### Purpose
Long-lived API tokens for **human users** who need programmatic access:
- Data analysts running pyodk scripts in Jupyter notebooks
- Researchers with dynamic IPs (travel, home ISP rotation, VPNs)
- Development and testing environments
- Any API access requiring longer-lived credentials

### Authentication Method

#### **Token Creation (TOTP-Protected)**
- **UI**: Web interface → User Profile → API Tokens
- **Endpoint**: `POST /v1/users/:id/api-tokens`
- **Requirements**: TOTP verification code (if 2FA enabled)
- **Token Format**: `vg_tkn_<random_32_chars>_<checksum>`
- **Lifetime**: 30-365 days (configurable, default 90 days)
- **Visibility**: Displayed ONCE at creation (like GitHub Personal Access Tokens)

```json
POST /v1/users/5/api-tokens
Authorization: Cookie __Host-session=...
{
  "name": "Jupyter Notebook - Data Analysis",
  "description": "Monthly data extraction scripts",
  "lifetimeDays": 90,
  "totpToken": "123456"  // Required if user has 2FA enabled
}

Response 201:
{
  "id": 42,
  "fullToken": "vg_tkn_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6_q7r8",
  "tokenPrefix": "vg_tkn_a1b2c3d4...",
  "name": "Jupyter Notebook - Data Analysis",
  "expiresAt": "2026-05-10T08:32:29.000Z",
  "createdAt": "2026-02-09T08:32:29.000Z",
  "warning": "This is the only time the full token will be displayed. Save it securely."
}
```

#### **Token Usage**
```bash
# Use in API requests
curl -H "Authorization: Bearer vg_tkn_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6_q7r8" \
  https://central.example.com/v1/projects

# pyodk configuration (future enhancement)
# [central]
# base_url = "https://central.example.com"
# token = "vg_tkn_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6_q7r8"
```

### Token Management

**List Tokens**
```json
GET /v1/users/5/api-tokens

Response 200:
[
  {
    "id": 42,
    "tokenPrefix": "vg_tkn_a1b2c3d4...",
    "name": "Jupyter Notebook",
    "description": "Monthly data extraction",
    "createdAt": "2026-02-09T08:32:29.000Z",
    "expiresAt": "2026-05-10T08:32:29.000Z",
    "lastUsedAt": "2026-02-09T10:15:00.000Z"
  }
]
```

**Revoke Token**
```json
DELETE /v1/users/5/api-tokens/42

Response 200:
{ "success": true }
```

### Security Features
- **TOTP-Protected Creation**: Prevents attacker with stolen session from creating long-lived tokens
- **bcrypt Hashed Storage**: Never stored in plaintext (like passwords)
- **Immediate Revocation**: Deleted tokens stop working immediately
- **Usage Tracking**: Last used timestamp for monitoring
- **Prefix-Only Display**: Full token shown only at creation

### IP Whitelist Policy for API Tokens

**Regular Users (Default):**
- API tokens NOT subject to IP whitelist
- Allows use from anywhere (travel, dynamic IPs)

**Service Accounts (See Section 1c):**
- API tokens MUST comply with mandatory IP whitelist
- Enforced for all authentication methods

---

## 1c. Service Accounts (NEW - 2026-02-09)

### Purpose
Web user accounts designated for **automated systems** (not humans):
- CI/CD pipelines (Jenkins, GitHub Actions)
- Scheduled data exports (cron jobs)
- Dashboard integrations (Power BI, Tableau)
- Server-to-server API communication

### Designation

**Marking as Service Account:**
- **UI**: Web interface → User Edit → Service Account Settings
- **Endpoint**: `PATCH /v1/users/:id/service-account`
- **Requirement**: Must have IP whitelist configured BEFORE marking
- **Effect**: Enforces stricter security policies

```json
PATCH /v1/users/10/service-account
{
  "isServiceAccount": true
}

Response 200:
{ "success": true }

// Error if no IP whitelist:
Response 403:
{
  "code": 403.1,
  "message": "Cannot mark as service account: IP whitelist must be configured first"
}
```

### Security Differences vs Regular Web Users

| Feature | Regular Web User | Service Account |
|---------|-----------------|----------------|
| **Session Lifetime** | 24 hours | **1 hour** |
| **API Token Lifetime** | 30-365 days | 30-365 days (same) |
| **IP Whitelist** | Optional | **MANDATORY** (for all auth methods) |
| **Audit Logging** | Standard | **Flagged as serviceAccount: true** |
| **Use Case** | Human administrators | Automated systems |

### Enforcement Rules

**Mandatory IP Whitelist:**
- Service accounts CANNOT authenticate without IP whitelist configured
- Applies to BOTH:
  - Session-based authentication (POST /v1/sessions)
  - API token authentication (Bearer vg_tkn_...)
- Rejected if IP not in whitelist: `403 Forbidden - IP not whitelisted`

**Shorter Session Lifetime:**
- Regular users: 24 hours
- Service accounts: 1 hour
- Reduces exposure window if token stolen

**Audit Logging:**
```json
// All actions by service accounts include:
{
  "actorId": 10,
  "action": "project.list",
  "serviceAccount": true,  // NEW FLAG
  "clientIp": "192.168.1.50",
  "timestamp": "2026-02-09T10:30:00.000Z"
}
```

### Configuration Steps

1. **Create web user** (or use existing)
2. **Configure IP whitelist** (minimum 1 entry required)
   ```json
   POST /v1/users/10/ip-whitelist
   {
     "ipCidr": "192.168.1.0/24",
     "description": "CI/CD server subnet"
   }
   ```
3. **Mark as service account**
   ```json
   PATCH /v1/users/10/service-account
   { "isServiceAccount": true }
   ```
4. **Authenticate normally** (sessions or API tokens)
   - All requests must come from whitelisted IPs
   - Sessions expire in 1 hour (not 24)

### Best Practices

✅ **Recommended:**
- Dedicated account per automation (e.g., "GitHub Actions", "Daily Export Cron")
- Minimal role assignment (viewer, not admin)
- Document IP whitelist entries with clear descriptions
- Monitor audit logs for unusual activity

❌ **Avoid:**
- Reusing human user accounts for automation
- Broad IP ranges (/16 or larger) without justification
- Assigning admin role unless absolutely necessary

---

## 2. App Users (Mobile Data Collectors)

### Purpose
Mobile data collection users who:
- Use **ODK Collect** on Android devices
- Submit form data to specific projects
- Need offline-capable authentication
- Cannot use web interface

### Authentication Method

#### **Password-Based Login**
- **Endpoint**: `POST /projects/:projectId/app-users/login`
- **Credentials**: Username + Password
- **Response**: Short-lived bearer token (no cookies)
- **Token Type**: Bearer (must be sent in `Authorization` header)
- **Expiration**: Configurable (default 3 days via `vg_app_user_session_ttl_days`)

```json
POST /projects/1/app-users/login
{
  "username": "collector-01",
  "password": "CollectPass!1",
  "deviceId": "android-tablet-01",
  "comments": "Tablet assigned to field worker"
}

Response 200:
{
  "id": 42,
  "token": "abcd1234efgh5678...",
  "projectId": 1,
  "expiresAt": "2026-02-11T08:32:29.000Z",
  "serverTime": "2026-02-08T08:32:30.000Z"
}
```

### Key Characteristics
- **Project-Scoped**: Each app user belongs to a single project
- **No Cookies**: All requests use Bearer token in `Authorization` header
- **No Web Access**: Cannot log into web interface
- **Session Cap**: Configurable limit on concurrent sessions per user (default 3)
- **Session History**: All sessions tracked with device info for admin review

### Session Management
```
Authorization: Bearer abcd1234efgh5678...
```

All API requests must include the token:
- Form list retrieval
- Form definition download
- Submission upload
- Attachment upload

### Security Features
- **Rate Limiting**: 5 failed attempts per username+IP in 5 minutes → 10-minute lockout
- **IP Tracking**: Per IP and per username tracking
- **Session Revocation**:
  - Self-revoke: User can revoke their own current session
  - Admin-revoke: Project managers can revoke all sessions for a user
- **Password Reset**: Admin can force password reset (terminates all sessions)
- **User Deactivation**: Admin can mark user inactive (blocks all authentication)

### VG Customizations
**Upstream ODK Central** uses public key authentication for app users (see below).
**VG Fork** replaces this with username/password authentication because:
- Easier for non-technical users
- No need to manage public/private key pairs
- Better UX for ODK Collect users
- Aligned with traditional mobile app authentication patterns

#### Database Architecture
- `field_keys` table: Links app user to project (upstream table, unchanged)
- `vg_field_key_auth` table: Stores VG-specific auth data (username, password hash, phone, active status)
- One-to-one relationship via `actorId` (FK to `field_keys.actorId`)

---

## 3. Public Key Authentication (API Users)

### Purpose
**Upstream ODK Central's default** for programmatic API access and data collection:
- Automated scripts and integrations
- Service accounts
- ODK Collect (upstream uses this, VG uses passwords instead)

### Authentication Method

#### **RSA Public Key**
- **Setup**: Generate RSA key pair, upload public key to server
- **Auth**: Sign requests with private key
- **Token**: Long-lived bearer token (can be months/years)
- **No Password**: Authentication via cryptographic signatures

```bash
# Generate key pair
openssl genpkey -algorithm RSA -out private_key.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in private_key.pem -out public_key.pem

# Upload public key via web UI or API
# Receive long-lived token
```

### Key Characteristics
- **Project-Scoped**: Like app users, scoped to a project
- **Long-Lived Tokens**: No expiration (until explicitly revoked)
- **No Interactive Login**: Keys are uploaded, tokens are generated
- **Cryptographic Security**: Private key never sent to server
- **No IP Whitelist**: Public key auth is NOT subject to IP restrictions (field keys bypass IP whitelist)

### VG Status
⚠️ **Not modified by VG fork** - still available but not primary method for app users.

VG's password-based app users coexist with upstream's public key mechanism:
- VG adds `vg_field_key_auth` table for passwords
- Upstream `field_keys` table unchanged
- Both authentication methods work simultaneously
- Public keys can still be used for API automation

---

## 4. IP Whitelist Policy (VG Feature)

### Overview
**IP Whitelist** restricts **Bearer token API access** to specific IP addresses or CIDR ranges.

**Policy (Updated 2026-02-09):**
- **Regular web users**: Optional (if configured, enforced for sessions and API tokens)
- **Service accounts**: **MANDATORY** (must have at least 1 entry, enforced for all auth methods)
- **App users**: Not applicable
- **Public keys**: Bypass whitelist (field keys)

### What It Protects

| Auth Type | Regular User | Service Account | App User | Public Key |
|-----------|-------------|-----------------|----------|-----------|
| **Web Login (Cookie)** | ❌ No | ❌ No | N/A | N/A |
| **Session Bearer Token** | ✅ If configured | **✅ MANDATORY** | N/A | N/A |
| **API Token (vg_tkn_...)** | ❌ No | **✅ MANDATORY** | N/A | N/A |
| **App User Token** | N/A | N/A | ❌ No | N/A |
| **Field Key Token** | N/A | N/A | N/A | ❌ No |

### How It Works (Updated 2026-02-09)

#### **Enforcement Logic** (from `lib/http/preprocessors.js`)

```javascript
// IP whitelist enforcement:
// 1. Applies to user type = 'user' (NOT 'field_key' or app users)
// 2. Applies to bearer token auth (NOT cookie auth)
// 3. SERVICE ACCOUNTS: ALWAYS enforced (mandatory)
// 4. REGULAR USERS: Enforced if whitelist configured (optional)

if (session.actor.type === 'user' && authMethod === 'bearer') {
  const user = await Users.getByActorId(session.actor.id);
  const hasWhitelist = await user.hasAnyIpWhitelistEntries();

  // SERVICE ACCOUNT: IP whitelist MANDATORY
  if (user.isServiceAccount) {
    if (!hasWhitelist) {
      return 403 Forbidden - "Service accounts must have IP whitelist configured"
    }
    if (!isIpWhitelisted(clientIp, user.whitelist)) {
      return 403 Forbidden - "IP not whitelisted"
    }
  }

  // REGULAR USER: IP whitelist OPTIONAL (only if configured)
  else if (hasWhitelist) {
    if (!isIpWhitelisted(clientIp, user.whitelist)) {
      return 403 Forbidden - "IP not whitelisted"
    }
  }
}
```

#### **Behavior:**

**Regular Web Users:**
- **No whitelist entries** → All IPs allowed (default)
- **Has whitelist entries** → Only whitelisted IPs allowed
- **API tokens (vg_tkn_)** → NOT subject to whitelist (allows travel/dynamic IPs)

**Service Accounts:**
- **No whitelist entries** → BLOCKED (cannot authenticate)
- **Has whitelist entries** → Only whitelisted IPs allowed
- **Both sessions AND API tokens** → Enforced
- **Whitelist check fails** → 403 Forbidden

### Configuration

#### **Database Schema**
```sql
CREATE TABLE vg_user_ip_whitelist (
  id SERIAL PRIMARY KEY,
  "actorId" INTEGER NOT NULL REFERENCES actors(id),
  ip_cidr CIDR NOT NULL,              -- PostgreSQL CIDR type
  description TEXT,
  enabled BOOLEAN DEFAULT true,
  created_by INTEGER REFERENCES actors(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### **CIDR Notation Support**
- **Single IP**: `192.168.1.100` or `192.168.1.100/32`
- **Subnet**: `192.168.1.0/24` (allows 192.168.1.0 - 192.168.1.255)
- **IPv6**: `2001:db8::/32`

### API Endpoints

```bash
# Get user's IP whitelist
GET /v1/users/:id/ip-whitelist
GET /v1/users/:id/ip-whitelist?enabled=true  # Only enabled entries

# Add IP to whitelist
POST /v1/users/:id/ip-whitelist
{
  "ipCidr": "192.168.1.0/24",
  "description": "Office network"
}

# Update entry (enable/disable, change IP, change description)
PATCH /v1/users/:id/ip-whitelist/:entryId
{
  "enabled": false,
  "description": "Temporarily disabled"
}

# Delete entry
DELETE /v1/users/:id/ip-whitelist/:entryId

# Check if specific IP is whitelisted (testing)
GET /v1/users/:id/ip-whitelist/check?ip=192.168.1.100
```

### Use Cases (Updated 2026-02-09)

#### **When to Use IP Whitelist**

**✅ MANDATORY for:**
- **Service accounts** (automated systems)
  - CI/CD pipelines
  - Scheduled cron jobs
  - Server-to-server integrations

**✅ RECOMMENDED for:**
- Web users accessing from static IPs (office networks)
- Additional security layer for administrative operations

**❌ NOT recommended for:**
- Human users with dynamic IPs (use API tokens instead)
- Laptop users who travel (use API tokens)
- App users (not supported)

#### **Example 1: Researcher with Laptop (API Token)**
Data analyst runs pyodk scripts from Jupyter notebook (travels frequently):
1. Log into web UI (with TOTP)
2. Create API token: "Jupyter Notebook - Data Analysis" (90 days)
3. Save token in pyodk config or environment variable
4. Token works from ANY IP (no whitelist required)
5. Revoke token if laptop stolen

#### **Example 2: CI/CD Pipeline (Service Account)**
GitHub Actions workflow calls API to export data daily:
1. Create web user: "GitHub Actions CI"
2. Add GitHub Actions IP range to whitelist: `192.0.2.0/24`
3. Mark as service account (enforces IP whitelist, 1hr sessions)
4. Workflow uses username/password or API token
5. All requests must come from whitelisted IPs

### Security Properties

#### **IP Determination**
```javascript
// Checks in order:
1. X-Forwarded-For header (from reverse proxy)
   - Takes FIRST IP in comma-separated list (original client)
2. request.ip (direct connection)
```

#### **CIDR Matching**
Uses PostgreSQL's native CIDR matching:
```sql
-- Check if IP is in CIDR range
WHERE '192.168.1.100'::inet <<= '192.168.1.0/24'::cidr
```

### Interaction with Other Security Features

| Feature | IP Whitelist | Interaction |
|---------|--------------|-------------|
| **2FA (TOTP)** | Protects API bearer token access | Protects web login |
| **Rate Limiting** | Applied before IP check | Applied after IP check |
| **Session Expiry** | Applied after IP check | Independent of IP |
| **Password Policy** | No interaction | No interaction |

### Audit Logging

All IP whitelist operations are audited:
```sql
-- Audit actions
'vg.ip_whitelist.create'   -- New entry added
'vg.ip_whitelist.update'   -- Entry modified
'vg.ip_whitelist.delete'   -- Entry removed

-- Audit details include
{
  "ipCidr": "192.168.1.0/24",
  "description": "Office network",
  "enabled": true
}
```

### Troubleshooting

#### **Common Issues**

**Problem:** User can log in but API calls fail with 403
```
Cause: IP whitelist is configured but current IP not in list
Solution: Check client IP with /ip-whitelist/check endpoint
```

**Problem:** Whitelist not enforced
```
Cause: Using cookie auth instead of bearer token
Solution: IP whitelist only applies to bearer token, not cookies
```

**Problem:** Public key auth ignores whitelist
```
Cause: By design - field keys are not subject to IP restrictions
Solution: This is expected behavior
```

### Best Practices

1. **Start with broad ranges, narrow down**
   - Begin with `/24` subnet, tighten to specific IPs later

2. **Add description to every entry**
   - Makes troubleshooting easier
   - Document the purpose: "Jenkins CI", "Power BI dashboard"

3. **Test before enabling**
   - Use `/ip-whitelist/check` endpoint to verify
   - Check with `curl -H "Authorization: Bearer $TOKEN"`

4. **Enable/disable, don't delete**
   - Temporarily disable entries instead of deleting
   - Preserves audit trail

5. **Monitor audit logs**
   - Watch for failed access attempts
   - Review whitelist changes regularly

6. **Combine with 2FA**
   - Use 2FA for web login
   - Use IP whitelist for API access
   - Defense in depth

---

## Comparison Matrix (Updated 2026-02-09)

### Session & Token Characteristics

| Feature | Web Users (Regular) | Web Users (Service Acct) | App Users (VG) | Public Keys |
|---------|-------------------|------------------------|----------------|-------------|
| **Auth Method** | Email/Password + TOTP OR API Token | Email/Password + TOTP OR API Token | Username/Password | RSA Public Key |
| **Token Storage** | Cookies + Optional API Tokens | Bearer Tokens (sessions + API tokens) | Bearer Token | Bearer Token |
| **Session Lifetime** | ~24 hours | **1 hour** | 3 days | Indefinite |
| **API Token Lifetime** | **30-365 days** | **30-365 days** | N/A | N/A |
| **2FA Support** | ✅ TOTP | ✅ TOTP | ❌ | ❌ |
| **Rate Limiting** | ✅ Per email+IP | ✅ Per email+IP | ✅ Per username+IP | ❌ |
| **Session Cap** | ❌ Unlimited | ❌ Unlimited | ✅ Configurable (3) | ❌ |
| **Project Scope** | ❌ System-wide | ❌ System-wide | ✅ Single project | ✅ Single project |
| **Web UI Access** | ✅ Full | ✅ Full | ❌ None | ❌ None |
| **API Access** | ✅ Cookies + Tokens | ✅ Bearer only | ✅ Bearer | ✅ Bearer |
| **Use Case** | Human admins | Automation (CI/CD) | Mobile data collection | Legacy automation |

### Security Controls (Updated 2026-02-09)

| Control | Web Users (Regular) | Web Users (Service Acct) | App Users | Public Keys |
|---------|-------------------|------------------------|-----------|------------|
| **Failed Login Lockout** | 5 attempts/5min → 10min | 5 attempts/5min → 10min | 5 attempts/5min → 10min | N/A |
| **IP Rate Limiting** | ✅ Per IP | ✅ Per IP | ✅ Per IP | N/A |
| **IP Whitelist** | ✅ Optional (if configured) | **✅ MANDATORY** | ❌ Not supported | ❌ Bypasses |
| **IP Whitelist (API Tokens)** | ❌ Not enforced | **✅ MANDATORY** | N/A | N/A |
| **Password Policy** | ✅ Complex | ✅ Complex | ✅ Complex | N/A |
| **Session Revocation** | ✅ Logout | ✅ Logout | ✅ Self + admin | ✅ Delete key |
| **API Token Revocation** | **✅ Per-token** | **✅ Per-token** | N/A | N/A |
| **Audit Logging** | ✅ Standard | **✅ Flagged (serviceAccount: true)** | ✅ Standard | ✅ Standard |
| **2FA Enforcement** | ✅ Role-based | ✅ Role-based | ❌ | ❌ |

---

## Configuration Settings

### System-Wide (Web Users)
- `sessionLifetime`: Session duration (default ~24h)
- `vg_totp_mandatory_roles`: Roles requiring 2FA (default `["admin"]`)
- `vg_web_user_lock_duration_minutes`: Lockout duration (default 10)

### Project-Level (App Users)
- `vg_app_user_session_ttl_days`: Token lifetime (default 3 days)
- `vg_app_user_session_cap`: Max concurrent sessions (default 3)
- Per-project overrides stored in `vg_project_settings`

---

## Migration Path (VG Fork)

### From Upstream Public Keys to VG Passwords

When migrating existing ODK Central instances:

1. **Existing field keys** (public keys) continue to work
2. **New app users** created via VG UI get username/password
3. **Dual authentication**: Both methods coexist
4. **Database**: `vg_field_key_auth` table added alongside `field_keys`

### Identification
- If `vg_field_key_auth.actorId` exists → password-based app user
- If only `field_keys.public` exists → public key-based user (upstream)

---

## API Endpoints Summary (Updated 2026-02-09)

### Web Users - Authentication
```
POST   /v1/sessions                              # Login (Phase 1 or complete)
POST   /v1/sessions/totp-verify                  # TOTP verification (Phase 2)
DELETE /v1/sessions/current                      # Logout
```

### Web Users - TOTP Management
```
POST   /v1/users/:id/totp/setup                  # Begin TOTP enrollment
POST   /v1/users/:id/totp/enable                 # Complete TOTP enrollment
POST   /v1/users/:id/totp/disable                # Disable 2FA
POST   /v1/users/:id/totp/dismiss-enrollment-prompt  # Dismiss optional prompt
GET    /v1/system/settings/totp-mandatory-roles  # Get mandatory roles
PUT    /v1/system/settings/totp-mandatory-roles  # Update mandatory roles
```

### Web Users - API Tokens (NEW - 2026-02-09)
```
GET    /v1/users/:id/api-tokens                  # List user's API tokens
POST   /v1/users/:id/api-tokens                  # Create new API token (requires TOTP)
DELETE /v1/users/:id/api-tokens/:tokenId         # Revoke API token
GET    /v1/users/:id/api-tokens/:tokenId/usage   # View token usage history
```

### Web Users - Service Accounts (NEW - 2026-02-09)
```
PATCH  /v1/users/:id/service-account             # Mark/unmark as service account
GET    /v1/users/:id                             # Get user (includes isServiceAccount field)
```

### Web Users - IP Whitelist
```
GET    /v1/users/:id/ip-whitelist                # List IP whitelist entries
POST   /v1/users/:id/ip-whitelist                # Add IP address/range
PATCH  /v1/users/:id/ip-whitelist/:entryId       # Update entry
DELETE /v1/users/:id/ip-whitelist/:entryId       # Delete entry
GET    /v1/users/:id/ip-whitelist/check?ip=...   # Test if IP is whitelisted
```

### App Users
```
POST   /projects/:id/app-users                   # Create app user
POST   /projects/:id/app-users/login             # Login (get token)
POST   /projects/:id/app-users/:id/password/change    # Self-change password
POST   /projects/:id/app-users/:id/password/reset     # Admin reset password
POST   /projects/:id/app-users/:id/revoke             # Self-revoke session
POST   /projects/:id/app-users/:id/revoke-admin       # Admin revoke all sessions
POST   /projects/:id/app-users/:id/active             # Admin activate/deactivate
GET    /projects/:id/app-users/:id/sessions           # View session history
```

### Public Keys (Unchanged Upstream)
```
POST   /projects/:id/app-users                   # Create with public key
GET    /projects/:id/app-users                   # List (token always null)
```

---

## References

- [VG API Documentation](vg_api.md)
- [App User Auth Routes](routes/app-user-auth.md)
- [Web User TOTP Routes](routes/web-user-totp.md)
- [Security Overview](vg_security.md)
- [System Settings](vg_settings.md)
