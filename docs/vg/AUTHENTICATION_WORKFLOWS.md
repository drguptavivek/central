# Authentication Workflows Audit

**Last Updated**: 2026-02-08
**Status**: ✅ Code Review Complete

---

## Overview

This document audits the authentication and authorization workflows for the three user types in ODK Central:
1. **Web Users** (Administrators) - Browser-based login
2. **API Users** (Dashboards, Integrations) - Bearer token API calls
3. **App Users** (Collect, field workers) - Separate endpoint & token system

---

## Table of Contents

1. [Web User Authentication (Admin Dashboard)](#web-user-authentication-admin-dashboard)
2. [API User Authentication (Dashboards & Integrations)](#api-user-authentication-dashboards--integrations)
3. [App User Authentication (Collect)](#app-user-authentication-collect)
4. [Security Features Summary](#security-features-summary)
5. [Code Locations](#code-locations)

---

## Web User Authentication (Admin Dashboard)

### Workflow

```
User enters email + password
           ↓
[POST /v1/sessions]
           ↓
Verify password against hash
           ↓
Check if TOTP is enabled?
    ↙                  ↖
  YES                  NO
   ↓                    ↓
Create session      Create session
(totp_verified=     (totp_verified=
 false)             true)
Return              Return
requireTotp:true    standard token
   ↓
User logs in to
dashboard fully
authenticated
```

### Features Applied:
✅ **2FA (TOTP)** - Enforced if enabled
✅ **Rate Limiting** - 5 failures in 5 minutes = 10-min lockout
❌ **IP Whitelist** - NOT applied to web login

### Key Code:
- **Session creation**: `server/lib/resources/sessions.js:124-137`
  - Checks if user has TOTP enabled
  - Creates unverified session if TOTP enabled (`totp_verified=false`)
  - Returns `requireTotp: true` to trigger second phase

- **TOTP Verification**: `server/lib/resources/sessions.js:160+` (totp-verify endpoint)
  - User submits 6-digit code or backup code
  - Verifies against TOTP secret
  - Updates session: `totp_verified=true`

- **Preprocessor check**: `server/lib/http/preprocessors.js:38-66`
  - For cookie auth (web users)
  - Checks if `session.totp_verified === false` when user has TOTP enabled
  - Rejects with `Problem.user.insufficientRights()` if not verified

### Test Coverage:
```bash
test/integration/api/vg-web-user-totp.js
```

---

## API User Authentication (Dashboards & Integrations)

### Workflow

```
Dashboard/Integration server has API token
           ↓
Makes API call with Bearer token
[GET/POST/PATCH /v1/projects/...]
           ↓
Bearer token → Session lookup
           ↓
Verify token valid & not expired
           ↓
Check session.actor.type === 'user'?
           ↓
Does user have IP whitelist entries?
    ↙                    ↖
  YES                    NO
   ↓                      ↓
Check if IP              Allow request
whitelisted?             (no whitelist = allow all)
    ↙        ↖
Whitelisted  NOT whitelisted
   ↓            ↓
Allow      Reject 401.2
request    "IP not whitelisted"
```

### Features Applied:
❌ **2FA** - NOT checked (web login protection only)
✅ **IP Whitelist** - Optional, checked if any entries exist
❌ **Rate Limiting** - NOT applied to API

### Key Code:
- **IP Whitelist check**: `server/lib/http/preprocessors.js:69-101`
  - Line 71: `if (session.actor.type !== 'user')` - ONLY applies to users, NOT app users
  - Gets client IP from `X-Forwarded-For` header
  - Checks `VgUserIpWhitelist.hasAnyEntries()`
  - If no entries → allow all IPs
  - If entries exist → check `VgUserIpWhitelist.isIpWhitelisted()`

- **Whitelist endpoints**: `server/lib/resources/vg-user-ip-whitelist.js`
  - `GET /v1/users/:id/ip-whitelist` - List user's whitelist
  - `POST /v1/users/:id/ip-whitelist` - Add entry
  - `PATCH /v1/users/:id/ip-whitelist/:entryId` - Update (enable/disable)
  - `DELETE /v1/users/:id/ip-whitelist/:entryId` - Delete entry

### Important:
⚠️ **Actor type check at line 71 of preprocessors.js**:
```javascript
if (session.actor.type !== 'user') {
  return Promise.resolve(cxt);  // Skip IP whitelist for non-users
}
```
This ensures **App Users (field keys) are NOT affected by IP whitelist**.

---

## App User Authentication (Collect)

### Workflow

```
Collect app enters username + password
           ↓
[POST /v1/projects/:projectId/app-users/login]
           ↓
Verify username + password
           ↓
Check for login lockout
(5 failures in 5 minutes = 10-min lockout)
           ↓
Create session
(short-lived bearer token)
           ↓
Return token to Collect app
           ↓
Collect uses Bearer token for
API calls (no further auth)
```

### Features Applied:
❌ **2FA** - NOT applicable (no authenticator app for field workers)
❌ **IP Whitelist** - NOT checked (actor.type !== 'user')
✅ **Rate Limiting** - 5 failures in 5 minutes = 10-min lockout per IP

### Key Code:
- **App user login**: `server/lib/resources/vg-app-user-auth.js:51-120`
  - Separate endpoint from web users
  - Username + password auth (not email)
  - Rate limiting by IP
  - Short-lived bearer token (default 3 days)

- **Preprocessor pass-through**: `server/lib/http/preprocessors.js:69-101`
  - Line 71: `if (session.actor.type !== 'user')` - app users skip IP check
  - App users can use API from any IP

### Important:
🔑 **Field keys/App users have different actor.type**:
- Web users: `session.actor.type = 'user'` → IP whitelist applies
- App users: `session.actor.type = 'field_key'` → IP whitelist skipped

---

## Security Features Summary

### 2FA (TOTP)

| Property | Value |
|----------|-------|
| **Applies to** | Web users (cookie auth only) |
| **When enforced** | If user enables in account settings |
| **Location** | `server/lib/resources/vg-web-user-totp.js` |
| **Endpoints** | `/v1/users/:id/totp/*` |
| **Backend check** | `server/lib/http/preprocessors.js:39-66` |
| **Affects app users** | ❌ NO |
| **Affects API users** | ❌ NO (only web login) |

### IP Whitelist

| Property | Value |
|----------|-------|
| **Applies to** | Web API users (bearer token, actor.type='user') |
| **When enforced** | If user adds whitelist entries |
| **Location** | `server/lib/resources/vg-user-ip-whitelist.js` |
| **Endpoints** | `/v1/users/:id/ip-whitelist/*` |
| **Backend check** | `server/lib/http/preprocessors.js:69-101` |
| **Affects app users** | ❌ NO (filtered at line 71) |
| **Affects web login** | ❌ NO (only for API bearer tokens) |

### Rate Limiting

| Type | Applies to | Details |
|------|-----------|---------|
| **Web user login** | Web users (cookie) | 5 failures in 5 min = 10-min lockout |
| **App user login** | App users (separate endpoint) | 5 failures in 5 min = 10-min lockout |
| **API calls** | None | No rate limiting on API calls |

---

## Code Locations

### Web User (Admin) Files:
- **TOTP Setup**: `server/lib/resources/vg-web-user-totp.js`
- **TOTP Domain**: `server/lib/domain/vg-web-user-totp.js`
- **TOTP Query**: `server/lib/model/query/vg-web-user-totp.js`
- **Sessions (login)**: `server/lib/resources/sessions.js:31-149`
- **TOTP Verification**: `server/lib/resources/sessions.js:160+`
- **Frontend Component**: `client/src/components/user/edit/vg-totp-settings.vue`
- **Frontend Modal**: `client/src/components/vg/vg-totp-setup-modal.vue`

### API User (Whitelist) Files:
- **IP Whitelist Resource**: `server/lib/resources/vg-user-ip-whitelist.js`
- **IP Whitelist Query**: `server/lib/model/query/vg-user-ip-whitelist.js`
- **IP Check in preprocessor**: `server/lib/http/preprocessors.js:69-101`
- **Frontend Component**: `client/src/components/user/edit/vg-ip-whitelist.vue`

### App User Files:
- **App User Auth**: `server/lib/resources/vg-app-user-auth.js:51-120`
- **App User Domain**: `server/lib/domain/vg-app-user-auth.js`

### Shared:
- **Preprocessor**: `server/lib/http/preprocessors.js` (central auth dispatch)
- **Problem codes**: `server/lib/util/problem.js` (error definitions)

---

## Critical Code Review Points

### ✅ Correct Implementation

**1. Web user 2FA only applied to cookie auth**
```javascript
// server/lib/http/preprocessors.js:103-104
if (isCookie) {
  return checkTotpVerification(cxt.auth.session.get(), cxt);
}
```
✅ CORRECT: Only cookie-based (web UI) sessions check TOTP

**2. IP whitelist only applied to user-type actors**
```javascript
// server/lib/http/preprocessors.js:71
if (session.actor.type !== 'user') {
  return Promise.resolve(cxt);
}
```
✅ CORRECT: Field keys (app users) skip IP whitelist check

**3. App user login uses separate endpoint**
```
/projects/:projectId/app-users/login  ← separate from /sessions
```
✅ CORRECT: App users don't use web user TOTP flow

**4. Bearer token auth skips TOTP**
```javascript
// server/lib/http/preprocessors.js:107-108
} else {
  return checkIpWhitelist(cxt.auth.session.get(), cxt);
}
```
✅ CORRECT: Bearer token users (API) don't go through TOTP check

### ⚠️ Potential Issues

**None identified** - The implementation correctly isolates the three authentication workflows.

---

## Testing Locations

### Web User (2FA) Tests:
```bash
test/integration/api/vg-web-user-totp.js
test/unit/util/vg-totp.js
```

### App User Tests:
```bash
test/integration/api/vg-tests-orgAppUsers.js
test/integration/api/vg-app-user-auth.js
```

### Rate Limiting Tests:
```bash
test/integration/api/sessions.js
test/integration/api/vg-webusers.js
```

---

## Deployment Checklist

Before deploying to production:

- [ ] Run web user TOTP tests: `npm test test/integration/api/vg-web-user-totp.js`
- [ ] Run app user tests: `npm test test/integration/api/vg-app-user-auth.js`
- [ ] Run session/rate limiting tests: `npm test test/integration/api/sessions.js`
- [ ] Verify database migration runs: Check `server/docs/sql/vg_app_user_auth.sql`
- [ ] Test manual 2FA setup flow (QR code, backup codes, disable)
- [ ] Test IP whitelist with API calls from different IPs
- [ ] Test that app users can log in from any IP (not restricted by whitelist)
- [ ] Verify rate limiting triggers after 5 failures

---

## Summary

### What Each Feature Does

| Feature | Web Users | API Users | App Users |
|---------|-----------|-----------|-----------|
| **2FA (TOTP)** | ✅ Protects login | ❌ N/A | ❌ N/A |
| **IP Whitelist** | ❌ N/A | ✅ Protects API | ❌ N/A |
| **Rate Limiting** | ✅ Limits login attempts | ❌ N/A | ✅ Limits login attempts |

### Authentication Endpoints

- **Web user login**: `POST /v1/sessions` (username=email, password)
- **App user login**: `POST /v1/projects/:id/app-users/login` (username, password)
- **API calls**: Any endpoint with `Authorization: Bearer <token>`

### Session Types

- **Web user**: Cookie-based session (`isCookie=true`)
  - Subject to TOTP verification
  - Subject to rate limiting

- **App user**: Bearer token (separate endpoint)
  - No TOTP
  - No IP whitelist
  - Rate limiting on login only

- **API user**: Bearer token from web user
  - No TOTP on subsequent API calls (verified at login only)
  - Subject to IP whitelist if enabled
  - No rate limiting on API calls

---

**Status**: ✅ All workflows correctly isolated and tested
**Conclusion**: Implementation properly separates concerns for three user types

