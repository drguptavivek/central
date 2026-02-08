# Complete Authentication & Access Guide

**Last Updated**: 2026-02-08
**Covers**: Web Users, API Users, Collect/App Users, OData, Public Links

---

## Quick Reference Matrix

| User Type | Login Endpoint | Credential | For OData | For Collect | IP Whitelist? | 2FA? |
|-----------|----------------|-----------|-----------|------------|--------------|------|
| **Web Admin** | POST /sessions | email:password | ✅ YES | ❌ NO | ✅ Optional | ✅ Optional |
| **API User (Web Token)** | POST /sessions | email:password | ✅ YES | ❌ NO | ✅ Optional | ✅ (at login) |
| **Collect/App User** | POST /app-users/login | username:password | ❌ NO | ✅ YES | ❌ NO | ❌ NO |
| **OData (via token)** | Any token | Bearer Token | ✅ YES | ❌ NO | ✅ Checked | - |
| **Public Link** | None (embedded) | Token in URL | ❌ NO | ✅ YES | ❌ NO | ❌ NO |

---

## 1. WEB USER (Admin Dashboard)

### What is it?
Administrator account for managing projects, forms, and users.

### Login
```bash
POST /v1/sessions
{
  "email": "admin@example.com",
  "password": "MySecurePassword123!"
}

Response (if 2FA enabled):
{
  "requireTotp": true,
  "token": "temp_session_token"
}

Then submit TOTP:
POST /v1/sessions/totp-verify
{
  "token": "temp_session_token",
  "totp": "123456"
}

Final Response:
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expiresAt": "2026-02-15T10:00:00Z"
}
```

### Access Methods
- **Web Interface**: Cookie-based session (automatic via login)
- **API/OData**: Bearer token from login response
- **Basic Auth**: email:password in Authorization header

### Password
- **Type**: Email address + password
- **Set by**: Admin themselves (account creation or reset)
- **Requirements**: Min 10 chars, uppercase, lowercase, digit, special char

### Security Features
| Feature | Applied? | Details |
|---------|----------|---------|
| **2FA** | ✅ Optional | TOTP at login if enabled |
| **IP Whitelist** | ✅ Optional | Restricts API access if configured |
| **Rate Limiting** | ✅ Login only | 5 failures in 5 min = 10 min lockout |

### Example: Web Admin Accessing OData
```bash
# Step 1: Login (with 2FA if enabled)
curl -X POST https://central.example.com/v1/sessions \
  -d '{"email":"admin@example.com", "password":"MyPass123"}'

# Step 2 (if 2FA): Verify code
curl -X POST https://central.example.com/v1/sessions/totp-verify \
  -d '{"token":"...", "totp":"123456"}'

# Step 3: Query OData with bearer token
curl -H "Authorization: Bearer eyJhbGciOi..." \
  https://central.example.com/projects/1/forms/myform.svc/Submissions
```

---

## 2. API USER (Dashboards & Integrations)

### What is it?
Web user accessing data via API (bearer token or basic auth). Same person as Web User, different access method.

### Authentication Methods

#### Method A: Bearer Token (Recommended)
```bash
# Get token via web login (same as Web User)
curl -X POST https://central.example.com/v1/sessions \
  -d '{"email":"admin@example.com", "password":"MyPass123"}'

Response: { "token": "eyJhbGciOi..." }

# Use token for API calls
curl -H "Authorization: Bearer eyJhbGciOi..." \
  https://central.example.com/projects/1/forms/myform.svc/Submissions
```

#### Method B: Basic Auth (Less Secure)
```bash
# No login needed, credentials sent with each request
curl -H "Authorization: Basic YWRtaW5AZXhhbXBsZS5jb206TXlQYXNzMTIz" \
  https://central.example.com/projects/1/forms/myform.svc/Submissions

# (YWRtaW5AZXhhbXBsZS5jb206TXlQYXNzMTIz = base64(admin@example.com:MyPass123))
```

### Password
- **Type**: Email + password (same as Web User)
- **Set by**: Admin themselves
- **Used**: Every request (Basic Auth) or once (Bearer Token)

### Security Features
| Feature | Applied? | Details |
|---------|----------|---------|
| **2FA** | ✅ At login | Required to get bearer token, then skipped for API calls |
| **IP Whitelist** | ✅ Per API call | Checked with every API request if enabled |
| **Rate Limiting** | ❌ API calls | Only on login, not API call volume |

### Example: API User with IP Whitelist
```
Admin email: mary@example.com
IP Whitelist: 203.0.113.0/24 (office network)

From office (203.0.113.45):
  curl -H "Authorization: Bearer ..." /forms/.svc/Submissions
  → ✅ Allowed (IP in whitelist)

From home (192.0.2.1):
  curl -H "Authorization: Bearer ..." /forms/.svc/Submissions
  → ❌ Blocked (IP not in whitelist)
  Error: 401.2 "IP not whitelisted for this account"
```

---

## 3. COLLECT / APP USER (Field Worker Mobile App)

### What is it?
Field worker using ODK Collect app to submit forms. Uses separate authentication from web users.

### Login
```bash
POST /v1/projects/1/app-users/login
{
  "username": "tableau_sync",
  "password": "FieldKeyPassword456!"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expiresAt": "2026-02-11T10:00:00Z"
}
```

### Access Methods
- **Collect App**: Uses field key token (automatic after login)
- **Form Submission**: OpenRosa protocol (POST /submission)
- **API**: Cannot query data via OData ❌

### Password
- **Type**: Username (NOT email) + password
- **Set by**: Admin when creating app user
- **Requirements**: Min 10 chars, uppercase, lowercase, digit, special char
- **Reset**: Via API endpoint (auto-generate new)

### Security Features
| Feature | Applied? | Details |
|---------|----------|---------|
| **2FA** | ❌ NO | Field workers don't use authenticator apps |
| **IP Whitelist** | ❌ NO | Field keys bypass IP restrictions (work from any location) |
| **Rate Limiting** | ✅ Login only | 5 failures in 5 min per IP = 10 min lockout |

### Important Limitation
Field keys **CANNOT** query data via OData:
```bash
# ❌ This does NOT work
curl -H "Authorization: Bearer FIELD_KEY_TOKEN" \
  https://central.example.com/projects/1/forms/myform.svc/Submissions

Error: 401.2 Insufficient Rights
Reason: App users missing submission.read permission
```

### Example: Collect App Workflow
```
1. App downloads form from Central
   GET /projects/1/forms/myform (no auth needed)

2. Field worker fills form in Collect

3. Collect submits form
   POST /projects/1/submission
   Authorization: Bearer FIELD_KEY_TOKEN
   X-OpenRosa-Version: 1.0
   [Form XML + attachments]

4. Central accepts submission ✅
   Field worker can continue collecting
```

---

## 4. ODATA SERVICE (Tableau, Power BI, Dashboards)

### What is it?
REST API for querying submission data. Used by business intelligence tools.

### Endpoints
```
Service metadata:     GET /projects/:id/forms/:form.svc
Submissions list:     GET /projects/:id/forms/:form.svc/Submissions
Single submission:    GET /projects/:id/forms/:form.svc/Submissions(':uuid')
With filters:         GET /projects/:id/forms/:form.svc/Submissions?$filter=...
```

### Who Can Access OData?

#### ✅ Can Access:
- **System Admins** - All forms
- **Project Managers** - Forms they manage
- **Project Viewers** - Forms they view (read-only)

#### ❌ Cannot Access:
- **App Users (Field Keys)** - Missing `submission.read` permission
- **Public Links** - No OData access

### Permission Check
```javascript
// Every OData request checks:
auth.canOrReject('submission.read', form)
```

For app users to access OData, they would need this role:
```javascript
const appUserVerbs = [
  'form.list',
  'form.read',
  'submission.create',
  'submission.read'  // ← Currently missing!
];
```

### Authentication
OData uses same auth as API (choose one):

#### Option A: Bearer Token
```bash
# 1. Get token (admin login)
TOKEN=$(curl -X POST https://central.example.com/v1/sessions \
  -d '{"email":"admin@example.com", "password":"MyPass"}' \
  | jq -r '.token')

# 2. Use in OData query
curl -H "Authorization: Bearer $TOKEN" \
  https://central.example.com/projects/1/forms/myform.svc/Submissions
```

#### Option B: Basic Auth
```bash
curl -u admin@example.com:MyPassword \
  https://central.example.com/projects/1/forms/myform.svc/Submissions
```

### Password
- **Type**: Same as Web User (email:password)
- **Note**: Cannot use field key credentials (missing permission)

### Security Features
| Feature | Applied? | Details |
|---------|----------|---------|
| **2FA** | ✅ At login | Must pass TOTP to get bearer token |
| **IP Whitelist** | ✅ Per request | Checked on every OData query if enabled |
| **Rate Limiting** | ❌ API calls | Only on login, not OData query volume |

### Example: Tableau with Admin Token
```bash
1. Admin logs in and gets bearer token
2. Tableau configures OData data source:
   URL: https://central.example.com/projects/1/forms/myform.svc
   Auth: Bearer Token

3. Tableau queries:
   GET /projects/1/forms/myform.svc/Submissions
   → Returns all submissions ✅

4. If admin has IP whitelist (203.0.113.0/24):
   From office (203.0.113.45): ✅ Allowed
   From home (192.0.2.1):      ❌ Blocked
```

---

## 5. PUBLIC LINK (Anonymous Access)

### What is it?
Anonymous, read-only access to specific forms. No login required.

### How to Create
```bash
POST /v1/projects/:id/forms/:formId/public-links
{
  "displayName": "Public Survey"
}

Response:
{
  "token": "d7ed2df0...",
  "displayName": "Public Survey",
  "createdAt": "2026-02-08T10:00:00Z"
}
```

### Access URL
```
Form Download:    https://central.example.com/projects/1/forms/myform
Submission:       https://central.example.com/key/d7ed2df0.../projects/1/submission
```

### Authentication
- **No login required**
- **Token embedded in URL**
- **Read-only access** to form + submission capability

### Password
- **Not used** - Public access, no credentials

### Security Features
| Feature | Applied? | Details |
|---------|----------|---------|
| **2FA** | ❌ N/A | No login |
| **IP Whitelist** | ❌ NO | Public access, any IP allowed |
| **Rate Limiting** | ❌ NO | No rate limits on public forms |

### Capabilities
- ✅ Download empty form
- ✅ Submit completed form (OpenRosa)
- ❌ Query submission data (no OData)

### Example: Public Survey Form
```
Admin creates public link

Public user (no account):
  1. Visit: https://central.example.com/projects/1/forms/myform
  2. Download form to Collect
  3. Fill form offline
  4. Submit form (automatic after internet)

Result: ✅ Submission received, no login needed
```

---

## Comparison: Which User for Which Purpose?

| Purpose | User Type | Password Type | 2FA | IP Whitelist | Best For |
|---------|-----------|---------------|-----|--------------|----------|
| **Admin dashboard** | Web Admin | Email:password | ✅ | ✅ | System administration |
| **API integration** | API User (Web) | Email:password | ✅ | ✅ | Dashboards, custom apps |
| **Field data collection** | App User | Username:password | ❌ | ❌ | ODK Collect, field workers |
| **BI tool queries** | OData (Web) | Email:password | ✅ | ✅ | Tableau, Power BI |
| **Public form** | Public Link | None | ❌ | ❌ | External surveys |

---

## Password Comparison

| User Type | Email or Username | Password Set By | Min Length | Special Chars | When Used |
|-----------|-------------------|-----------------|-----------|---------------|-----------|
| **Web Admin** | email | Self | 10 | ✅ Required | Every login |
| **API User** | email | Self | 10 | ✅ Required | Login or each API call (Basic Auth) |
| **App User** | username (NOT email) | Admin | 10 | ✅ Required | Each Collect login |
| **OData** | email | Self | 10 | ✅ Required | Via web login |
| **Public** | None | N/A | N/A | N/A | Not applicable |

---

## Security Features - Complete Matrix

### 2FA (Two-Factor Authentication)

```
Applied where:
├─ Web User login → ✅ REQUIRED (if enabled)
├─ API User login → ✅ REQUIRED (if enabled, to get token)
├─ API calls using token → ❌ Skipped
├─ App User login → ❌ Not applicable
├─ OData queries → ❌ Skipped (but 2FA at web login)
└─ Public Link → ❌ N/A

Important: 2FA only protects LOGIN, not API access
```

### IP Whitelist

```
Applied where:
├─ Web User API calls → ✅ Per request (if enabled)
├─ Web User OData queries → ✅ Per request (if enabled)
├─ App User submission → ❌ Skipped (field keys bypass)
├─ App User OData query → ❌ (doesn't work anyway)
├─ Public Link → ❌ No restriction
└─ Web login → ❌ Not checked

Code filter: if (actor.type !== 'user') { skip IP whitelist }
  ↑ Field keys have actor.type='field_key' → skipped
```

### Rate Limiting

```
Applied where:
├─ Web User login attempts → ✅ 5 failures in 5 min = 10 min lockout
├─ Web User API calls → ❌ No limit
├─ App User login attempts → ✅ 5 failures in 5 min = 10 min lockout
├─ App User submission → ❌ No limit
├─ OData queries → ❌ No limit
└─ Public submission → ❌ No limit
```

---

## Common Scenarios

### Scenario 1: Tableau Server with Admin Token
```
Admin: alice@example.com
2FA: Enabled (Google Authenticator)
IP Whitelist: 203.0.113.0/24

Tableau setup:
1. Admin logs in: alice@example.com + password
2. Admin enters 6-digit TOTP code
3. System gives bearer token
4. Tableau stores bearer token
5. Tableau queries OData every hour

Result:
✅ Works (admin has submission.read)
✅ 2FA protects at login
✅ IP checked per query (office only)
```

### Scenario 2: Field Worker Submitting Data
```
App User: john_collector (username, NOT email)
App created by: admin
IP: Any (VPN, home, office, mobile)

Workflow:
1. John logs in: POST /app-users/login
   username: john_collector
   password: auto-generated by admin
2. Collect app gets bearer token
3. John collects form data offline
4. John submits form: OpenRosa POST /submission
5. John can collect more (no IP restrictions)

Result:
✅ Works from any location (no IP whitelist)
✅ Can submit forms (has submission.create)
❌ Cannot query data (no submission.read)
```

### Scenario 3: Power BI with Field Key (FAILS)
```
Setup attempt:
Username: tableau_sync (app user)
Password: field key credentials
URL: /projects/1/forms/myform.svc/Submissions

What happens:
✅ Login succeeds (gets field key token)
❌ OData query FAILS (missing submission.read permission)

Error: 401.2 Insufficient Rights

Why: App users only have:
- form.list ✅
- form.read ✅
- submission.create ✅
- submission.read ❌ Missing!
```

### Scenario 4: Public Survey
```
Admin creates public form

Anonymous user workflow:
1. Visit: https://central.example.com/projects/1/forms/myform
2. No login required
3. Download form to Collect
4. Fill form
5. Submit (automatic when online)

Result:
✅ No credentials needed
✅ Form submitted successfully
❌ Cannot see other submissions (public is write-only)
```

---

## Code Reference

### Permission Check (OData)
```javascript
// lib/resources/odata.js:85
.then((form) => auth.canOrReject('submission.read', form))
```

### Role Definitions
- **Admin**: `lib/model/migrations/20181212-01-add-roles.js:51` (all verbs)
- **App User**: `lib/model/migrations/20181212-01-add-roles.js:54` (form.list, form.read, submission.create)
- **Project Manager**: `lib/model/migrations/20190227-01-add-project-manager-role.js`
- **Project Viewer**: `lib/model/migrations/20190923-01-add-project-viewer-role.js`

### Authentication Handler
```javascript
// lib/http/preprocessors.js:37-187
// Processes: Field keys, Bearer tokens, Basic auth, Cookies
```

### OData Endpoints
```javascript
// lib/resources/odata.js:80-91
odataResource('/projects/:projectId/forms/:xmlFormId.svc', false, ...)
```

---

## Summary

**5 User Types**:
1. **Web User** - Admin dashboard + API access
2. **API User** - Web user via bearer token or basic auth
3. **App/Collect User** - Field worker, form submission only
4. **OData User** - BI tools querying data (same auth as API User)
5. **Public Link** - Anonymous form access

**Key Rules**:
- ✅ Admin has all permissions
- ✅ Web users can access both web UI and OData
- ❌ App users cannot access OData (missing permission)
- ✅ Public links work, but read/write only (no OData)
- ✅ IP whitelist protects web user API calls
- ❌ IP whitelist doesn't restrict field keys
- ✅ 2FA required at login, not for API calls
