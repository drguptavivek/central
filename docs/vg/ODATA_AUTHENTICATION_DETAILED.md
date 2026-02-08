# OData Authentication Mechanisms - Complete Guide

**Last Updated**: 2026-02-08

---

## Table of Contents

1. [OData Overview](#odata-overview)
2. [Authentication Methods](#authentication-methods)
3. [User Types & Credentials](#user-types--credentials)
4. [Security Features Applied](#security-features-applied)
5. [How to Use OData](#how-to-use-odata)
6. [Common Use Cases](#common-use-cases)

---

## OData Overview

### What is OData?

OData (Open Data Protocol) is a standardized protocol for querying data via REST API. Tools like **Tableau** and **Power BI** use OData to access form submission data from Central.

### OData Endpoints in Central

```
Service Document (list of available data):
GET /projects/:projectId/forms/:xmlFormId.svc

Metadata (schema/structure):
GET /projects/:projectId/forms/:xmlFormId.svc/$metadata

Form Submissions Data:
GET /projects/:projectId/forms/:xmlFormId.svc/Submissions

Single Submission:
GET /projects/:projectId/forms/:xmlFormId.svc/Submissions(:uuid)

With query filters:
GET /projects/:projectId/forms/:xmlFormId.svc/Submissions?$filter=__status eq 'completed'
```

### OData is READ-ONLY for Data Access

- ✅ You can **query** form submission data
- ❌ You cannot **create** new submissions via OData (use OpenRosa for that)
- ❌ You cannot **delete** submissions via OData
- Permission: `submission.read` (read access to form submissions)

---

## Authentication Methods

OData supports **4 authentication methods**. The method you use depends on:
1. **Which user type you are** (web user vs app user)
2. **What credential you have** (password vs token)
3. **What client tool you're using** (Tableau vs custom script)

### Method 1: Field Key (App User Token) - RECOMMENDED FOR TABLEAU/POWER BI

#### Who Uses This?
- **Tableau Server** connecting to Central
- **Power BI** connecting to Central
- **Any BI tool** that needs a long-lived token
- **Mobile apps** (Collect)

#### What Credential You Need?
A **field key token** from an app user account. This is a long-lived bearer token.

#### How to Get It?

**Step 1: Create an App User** (Admin only)
```bash
POST /v1/projects/:projectId/app-users
{
  "displayName": "Tableau Data Sync",
  "username": "tableau_sync"
}
```
Response: Get the field key (looks like: `XXXX...XXXX`)

**Step 2: Get the token**
The response includes the field key token. Save it securely.

#### How to Use It?

**Option A: In URL (for some BI tools)**
```
https://central.example.com/key/FIELD_KEY_TOKEN/projects/1/forms/myform.svc/Submissions
```

**Option B: In Authorization Header (REST clients)**
```bash
curl -H "Authorization: Bearer FIELD_KEY_TOKEN" \
  https://central.example.com/projects/1/forms/myform.svc/Submissions
```

**Option C: In Tableau/Power BI Connection**
- URL: `https://central.example.com/projects/1/forms/myform.svc`
- Authentication: Select "OData"
- Username: `tableau_sync` (the app user username)
- Password: Leave blank (not used, token is in URL)

#### Security Features Applied?
| Feature | Applied? | Reason |
|---------|----------|--------|
| **2FA** | ❌ NO | Field keys don't trigger TOTP check (not cookie auth) |
| **IP Whitelist** | ❌ NO | Field keys skip IP whitelist (`actor.type='field_key'`) |
| **Rate Limiting** | ❌ NO | Rate limiting only applies to app-user login, not API calls |
| **Password** | ❌ NOT USED | Token-based auth, no password needed |

#### Important Restrictions?
- Field keys are **read-only** by default (can only access data)
- Field keys **cannot** be used to log into the web interface
- Field keys have **access only to the assigned project and form**

#### How Long is Token Valid?
- Default: **3 days** (but can be renewed)
- After expiration: Must get a new token

---

### Method 2: Bearer Token (Web User API Token) - FOR API INTEGRATIONS

#### Who Uses This?
- **Custom Python/Node.js scripts** accessing OData
- **Power BI Desktop** (local development)
- **Tableau Desktop** (local development)
- **Custom dashboards** built by developers

#### What Credential You Need?
A **bearer token** obtained by logging in as a web user.

#### How to Get It?

**Step 1: Log in as web user**
```bash
POST /v1/sessions
{
  "email": "admin@example.com",
  "password": "your_password"
}
```
Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiresAt": "2026-02-15T10:00:00Z"
}
```

**Step 2: Save the token for API calls**

#### But Wait! If 2FA is Enabled?
If your account has 2FA enabled, the login flow is different:

```bash
# Step 1: Login (will fail if 2FA is enabled)
POST /v1/sessions
{
  "email": "admin@example.com",
  "password": "your_password"
}

Response (if 2FA enabled):
{
  "requireTotp": true,
  "token": "temp_session_token"
}

# Step 2: Provide TOTP code
POST /v1/sessions/totp-verify
{
  "token": "temp_session_token",
  "totp": "123456"  // 6-digit code from authenticator app
}

# Step 3: Now you get the real token
Response:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### How to Use It?

```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  https://central.example.com/projects/1/forms/myform.svc/Submissions
```

#### Security Features Applied?
| Feature | Applied? | Reason |
|---------|----------|--------|
| **2FA** | ✅ YES | REQUIRED at login (web user) |
| **IP Whitelist** | ✅ YES | Applied if user has whitelist entries |
| **Rate Limiting** | ❌ NO | Only on login attempts, not API calls |
| **Password** | ✅ YES USED | Email + password for login |

#### Example Scenario:
```
1. Web admin has 2FA enabled with Google Authenticator
2. Admin logs in: email + password
3. Server asks for TOTP code
4. Admin enters 6-digit code from app
5. Server returns bearer token
6. Admin can now use token for OData queries
7. If admin has IP whitelist set to "192.168.1.0/24":
   - Queries from 192.168.1.50 → ALLOWED
   - Queries from 10.0.0.1 → DENIED (IP not whitelisted)
```

#### How Long is Token Valid?
- Depends on system configuration
- Typically: **24-30 days** (longer than field keys)
- Revoked if: Password changed, 2FA disabled, account suspended

---

### Method 3: Basic Auth (Web User Credentials) - LESS SECURE

#### Who Uses This?
- **Legacy systems** requiring Basic Auth
- **Some Tableau configurations** (older versions)
- **Power BI with special setup**

#### What Credential You Need?
**Email and password** (sent in Authorization header)

#### How to Use It?

```bash
# Base64 encode "email:password"
# For admin@example.com / mypassword123
# Encoded: YWRtaW5AZXhhbXBsZS5jb206bXlwYXNzd29yZDEyMw==

curl -H "Authorization: Basic YWRtaW5AZXhhbXBsZS5jb206bXlwYXNzd29yZDEyMw==" \
  https://central.example.com/projects/1/forms/myform.svc/Submissions
```

**In Tableau/Power BI:**
- URL: `https://central.example.com/projects/1/forms/myform.svc`
- Authentication: "OData" or "Basic"
- Username: `admin@example.com`
- Password: `your_password`

#### Important Security Note ⚠️
Basic Auth sends credentials **with every request**:
- ❌ Less secure than bearer tokens (which are short-lived)
- ❌ If credentials exposed, attacker can use them for login too
- ⚠️ MUST use HTTPS (will reject over HTTP)

#### Security Features Applied?
| Feature | Applied? | Reason |
|---------|----------|--------|
| **2FA** | ❌ NO | Basic Auth bypasses 2FA (treated as API access) |
| **IP Whitelist** | ✅ YES | Applied if user has whitelist entries |
| **Rate Limiting** | ❌ NO | No rate limiting on OData API calls |
| **Password** | ✅ YES USED | Email + password sent in header |

#### Comparison: Bearer Token vs Basic Auth
| Feature | Bearer Token | Basic Auth |
|---------|-------------|-----------|
| **Gets TOTP at login?** | ✅ Yes (once) | ❌ No (skipped) |
| **Gets IP checked at login?** | ❌ No | ❌ No |
| **Gets IP checked per request?** | ✅ Yes | ✅ Yes |
| **Credentials sent per request?** | ❌ No (token only) | ✅ Yes (email:password) |
| **Security** | ⭐⭐⭐ Higher | ⭐⭐ Lower |
| **Convenience** | ⭐⭐ Must renew token | ⭐⭐⭐ Always works |

---

### Method 4: Public Link - ANONYMOUS (if enabled)

#### Who Uses This?
- **Public dashboards** shared with anyone
- **Anonymous data access** (no login required)
- **Embedded reports** on public websites

#### What Credential You Need?
Just the public link URL (no password)

#### How to Use It?
```bash
curl https://central.example.com/projects/1/forms/myform/public-link-token.svc/Submissions
```

#### Security Features Applied?
| Feature | Applied? | Reason |
|---------|----------|--------|
| **2FA** | ❌ N/A | No login needed |
| **IP Whitelist** | ❌ NO | Public access, IP whitelist skipped |
| **Rate Limiting** | ❌ NO | No rate limiting |
| **Password** | ❌ N/A | Not used |

---

## User Types & Credentials

### Summary Table: Which User Type, Which Password?

| User Type | Created By | Uses What Credential | For OData Access? | Has 2FA? | IP Whitelist? |
|-----------|-----------|------------------|-------------------|----------|--------------|
| **Web User (Admin)** | Admin account | Email + Password | ✅ Yes (bearer token or basic) | ✅ Can enable | ✅ Can enable |
| **App User (Collect)** | Admin (per project) | Username + Password | ✅ Yes (field key token) | ❌ No | ❌ No |
| **Public Link** | Admin (per form) | None (embedded token) | ✅ Yes (read-only) | ❌ No | ❌ No |

### Web User
**Example**: `admin@example.com`
```bash
# Login with email + password
POST /v1/sessions
{
  "email": "admin@example.com",
  "password": "MySecurePassword123!"
}
```

### App User
**Example**: `tableau_sync` (username, NOT email)
```bash
# Get token with username + password
POST /v1/projects/1/app-users/login
{
  "username": "tableau_sync",
  "password": "FieldKeyPassword456!"
}
```

**Important Difference**: App user uses **username** (no @), web user uses **email**.

---

## Security Features Applied

### Feature 1: 2FA (TOTP)

#### When is 2FA checked?
- ✅ **Web user login** (when getting bearer token)
- ❌ **App user login** (field key)
- ❌ **Basic Auth** (OData access, not login)
- ❌ **Public Link** (no login)

#### What does this mean?
```
Scenario 1: Admin with 2FA trying to get bearer token
│
├─ POST /v1/sessions (email + password)
│   └─ Server: "Need TOTP code"
│
├─ POST /v1/sessions/totp-verify (TOTP code)
│   └─ Server: "Here's your bearer token"
│
└─ Use bearer token for OData queries (no more TOTP checks)

Scenario 2: Admin with 2FA using Basic Auth
│
├─ GET /forms/myform.svc/Submissions
├─ Authorization: Basic email:password
│   └─ Server: Accepts it (TOTP not checked for API access)
│
└─ Query succeeds (no TOTP needed for API calls)
```

#### **Key Point**: 2FA only protects **login**, not API access!

---

### Feature 2: IP Whitelist

#### When is IP whitelist checked?
- ✅ **Web user API access** (bearer token or basic auth, actor.type='user')
- ✅ **During web user API requests** (checked per request)
- ❌ **App user API access** (field keys skip IP check, actor.type='field_key')
- ❌ **App user login** (no IP whitelist on /app-users/login)
- ❌ **Public Link** (no IP restriction)

#### Code that filters:
```javascript
// Line 71 of server/lib/http/preprocessors.js
if (session.actor.type !== 'user') {
  return Promise.resolve(cxt);  // ← Field keys and public links skip this
}

// Only web users (actor.type='user') reach the IP whitelist check
```

#### Example Scenarios:

**Scenario 1: Tableau using field key from any IP**
```
Tableau in Office:    GET .../Submissions  (IP: 203.0.113.45)
                      → ALLOWED (field key, IP whitelist skipped)

Tableau from Home:    GET .../Submissions  (IP: 192.0.2.100)
                      → ALLOWED (field key, IP whitelist skipped)

Tableau from Coffee:  GET .../Submissions  (IP: 198.51.100.50)
                      → ALLOWED (field key, IP whitelist skipped)
```

**Scenario 2: Web user with IP whitelist set to "office only"**
```
Admin whitelist entries:
  - 203.0.113.0/24 (Office network)

Admin accessing from Office:
  GET .../Submissions  (IP: 203.0.113.45)
  → ALLOWED (IP in whitelist)

Admin accessing from Home:
  GET .../Submissions  (IP: 192.0.2.100)
  → DENIED (IP not in whitelist)
  Error: 401.2 "IP not whitelisted for this account"
```

#### **Key Point**: IP whitelist protects web users from **stolen API keys**, not field keys!

---

### Feature 3: Rate Limiting

#### When is rate limiting applied?
- ✅ **Web user login** (5 failures in 5 minutes = 10-min lockout)
- ✅ **App user login** (5 failures in 5 minutes = 10-min lockout per IP)
- ❌ **Bearer token API calls** (no rate limiting)
- ❌ **Field key API calls** (no rate limiting)
- ❌ **Basic auth API calls** (no rate limiting)

#### Example:
```
Admin tries to login 5 times with wrong password
  Attempt 1: FAILED
  Attempt 2: FAILED
  Attempt 3: FAILED
  Attempt 4: FAILED
  Attempt 5: FAILED

  → Account LOCKED for 10 minutes

After 10 minutes: Can try again
```

---

## How to Use OData

### Scenario 1: Tableau Server (Official Method)

**BEST APPROACH: Use Field Key**

```
Step 1: Admin creates app user for Tableau
  POST /v1/projects/1/app-users
  {
    "displayName": "Tableau Server Sync",
    "username": "tableau_sync"
  }

  Response includes field key (save this!)

Step 2: Configure in Tableau Server
  Data Source:
  - Type: OData
  - Server: central.example.com
  - URL: /projects/1/forms/myform.svc
  - Auth Method: OData Auth (or URL-based)
  - Field Key: XXXX...XXXX (paste the token)

Step 3: Refresh in Tableau
  - Tableau connects to /key/XXXX.../projects/1/forms/myform.svc
  - Gets list of form fields
  - Retrieves submission data
  - No TOTP needed
  - No IP whitelist restrictions
```

### Scenario 2: Power BI (Official Method)

**BEST APPROACH: Use Field Key**

```
Step 1-2: Same as Tableau (create app user, get field key)

Step 3: Configure in Power BI Desktop
  Get Data > OData Feed

  URL: https://central.example.com/key/XXXX.../projects/1/forms/myform.svc

  Authentication:
  - If prompted for password: Leave blank
  - Click Connect

Step 4: Load data
  - Power BI queries the OData endpoint
  - Gets form schema and submission data
  - Can refresh without re-authenticating
```

### Scenario 3: Custom Python Script

**APPROACH 1: Field Key (Simpler)**
```python
import requests

field_key = "XXXX...XXXX"
url = "https://central.example.com/key/{}/projects/1/forms/myform.svc/Submissions".format(field_key)

response = requests.get(url, headers={
    "Authorization": "Bearer {}".format(field_key)
})

data = response.json()
print(data)
```

**APPROACH 2: Bearer Token (Requires Login Each Time)**
```python
import requests

# Step 1: Login to get bearer token
login_url = "https://central.example.com/v1/sessions"
response = requests.post(login_url, json={
    "email": "admin@example.com",
    "password": "MyPassword123!"
})

if response.status_code == 401:
    # Check if 2FA is required
    if response.json().get("requireTotp"):
        # Need to verify TOTP code
        totp_code = input("Enter 6-digit TOTP code: ")
        verify_response = requests.post(
            "https://central.example.com/v1/sessions/totp-verify",
            json={
                "token": response.json()["token"],
                "totp": totp_code
            }
        )
        token = verify_response.json()["token"]
    else:
        raise Exception("Login failed")
else:
    token = response.json()["token"]

# Step 2: Use bearer token for OData queries
odata_url = "https://central.example.com/projects/1/forms/myform.svc/Submissions"
response = requests.get(odata_url, headers={
    "Authorization": "Bearer {}".format(token)
})

data = response.json()
print(data)
```

### Scenario 4: OData Client Tool (Excel Power Query, etc.)

```
Tool: Excel Power Query
Data > From OData Feed

URL:
- Option A (Field Key): https://central.example.com/key/XXXX.../projects/1/forms/myform.svc
- Option B (Basic Auth): https://central.example.com/projects/1/forms/myform.svc

Auth:
- Field Key: Leave empty (in URL)
- Basic Auth: Enter admin email + password

Connect and load data
```

---

## Common Use Cases

### Use Case 1: Tableau Server → Central (Production)

| Component | What to Use | Why |
|-----------|------------|-----|
| **Auth Method** | Field Key | Long-lived, no password expiration |
| **User Type** | App User | Can't access web interface, minimal permissions |
| **IP Whitelist** | Not needed | Field keys bypass it anyway |
| **2FA** | N/A | App users don't have 2FA |
| **Password** | App user password | Only needed once to create user |

```
Central:
  Admin creates app user "tableau"
  Saves field key token

Tableau Server:
  Receives field key token from Central admin
  Configures as OData data source
  Refreshes daily automatically
  No further credential needed
```

### Use Case 2: Developer Building Custom Dashboard

| Component | What to Use | Why |
|-----------|------------|-----|
| **Auth Method** | Bearer Token | Flexible, can use same admin account |
| **User Type** | Web User | Full access to data as admin |
| **IP Whitelist** | Optional | Protect from leaked tokens |
| **2FA** | ✅ Required | Admin account security |
| **Password** | Web user password | Admin email + password at login |

```
Developer:
  Logs in once: admin email + password
  Completes 2FA challenge
  Gets bearer token
  Uses token in dashboard API calls
  Token expires after ~30 days
  Re-login if needed

If IP whitelist set:
  Dashboard can only access from specified IPs
  Protects if token is leaked
```

### Use Case 3: Public Dashboard (No Authentication)

| Component | What to Use | Why |
|-----------|------------|-----|
| **Auth Method** | Public Link | No credentials needed |
| **User Type** | Public Link (special) | Read-only, no login |
| **IP Whitelist** | Not applicable | Public access |
| **2FA** | N/A | No login |
| **Password** | None | Not used |

```
Central Admin:
  Creates public link for form
  Shares URL publicly

Public User (no account):
  Visits shared URL
  Can view form data
  No login needed
  No credentials exposed
```

---

## Quick Reference: "What Password Do I Use?"

### Question: "I have Tableau. Which password?"

**Answer: You need a field key (not a password)**
```
1. Admin creates app user in Central
2. Admin gets field key (long token)
3. Admin gives this token to Tableau
4. Tableau uses token (no password needed)

If you use email+password:
  - You're using Basic Auth (less secure)
  - Your credentials sent with every request
  - Not recommended
```

### Question: "I'm a developer. Which password?"

**Answer: Your web user email + password**
```
1. You log in: admin@example.com + YourPassword123
2. If 2FA enabled: Enter 6-digit code from authenticator app
3. Server gives you bearer token
4. Use bearer token for API calls (no more password needed)
5. Token expires after ~30 days
6. Log in again to get new token

Do NOT use:
  - App user password (wrong user type)
  - Basic Auth (less secure, password sent each request)
```

### Question: "I'm an admin accessing from home. IP whitelist on?"

**Answer: Depends on how you authenticate**
```
If using bearer token (recommended):
  - First login from anywhere (gets token)
  - After that, IP whitelist is checked per request
  - If your home IP is not whitelisted → BLOCKED

If using basic auth:
  - IP whitelist checked with every request
  - If your home IP is not whitelisted → BLOCKED

Solution:
  - Whitelist your home IP
  - OR use VPN to office network
  - OR disable IP whitelist if not needed
```

---

## Troubleshooting

### "Authentication Failed" Error

**Check These:**
1. ✅ Are you using the right credential type?
   - Email for web users (admin@example.com)
   - Username for app users (tableau_sync)
   - Field key token for bearer token
2. ✅ Is credential correct (not expired)?
3. ✅ Is 2FA required? (check if requireTotp: true in response)

### "IP Not Whitelisted" Error

**Check These:**
1. ✅ Are you using field key? (field keys skip IP whitelist)
2. ✅ What's your current IP? (use curl -I to check)
3. ✅ Is it in whitelist? (check account settings)
4. ✅ Is whitelist enabled? (if no entries, all IPs allowed)

### "Insufficient Rights / Permission Denied"

**Check These:**
1. ✅ Does user have access to this project?
2. ✅ Does user have access to this form?
3. ✅ Does user have `submission.read` permission?

### Bearer Token Expired

**Solution:**
```bash
# Get new bearer token
POST /v1/sessions
{
  "email": "admin@example.com",
  "password": "YourPassword123"
}

# If 2FA required:
POST /v1/sessions/totp-verify
{
  "token": "temp_token",
  "totp": "123456"
}
```

---

**Summary**:
- **Tableau/Power BI**: Use field key (recommended)
- **Web API**: Use bearer token (get via login)
- **2FA**: Only at login, not on API calls
- **IP Whitelist**: Only for web user API access, not field keys
- **Passwords**: Different for web users (email) vs app users (username)
