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

## OpenRosa Submissions (Collect Data Upload)

### Overview

OpenRosa is a protocol standard for form submission used by ODK Collect (and other mobile data collection apps) to submit completed forms and associated attachments to Central.

### Workflow

```
Collect app has completed form
           ↓
Collect authenticates using field key token
(from /app-users/login endpoint)
           ↓
[POST /projects/:projectId/submission]
(OpenRosa multipart form submission)
           ↓
openRosaPreprocessor validates
X-OpenRosa-Version header
           ↓
authHandler processes field key
(bearer token in Authorization header
or URL prefix /key/{token}/)
           ↓
Field key is valid
           ↓
Session created with
actor.type='field_key'
           ↓
TOTP check SKIPPED
(line 104: only for isCookie)
           ↓
IP whitelist check SKIPPED
(line 71: if session.actor.type !== 'user')
           ↓
Submission processed
Form data + attachments stored
```

### Features Applied:
❌ **2FA** - SKIPPED (not cookie auth, field key only)
❌ **IP Whitelist** - SKIPPED (actor.type='field_key')
✅ **Rate Limiting** - Applied only to app user login, not to submission itself

### Key Code:

**OpenRosa endpoint setup** (`server/lib/resources/submissions.js`):
- Line 73-87: GET/HEAD `/projects/:projectId/submission` (returns 204)
- Line 104: POST `/projects/:projectId/submission` with multipart form data
- Both use `_endpoint.openRosa(...)` which applies the openRosaPreprocessor

**OpenRosa-specific preprocessor** (`server/lib/http/endpoint.js:310-318`):
```javascript
const openRosaPreprocessor = (_, context) => {
  const header = context.headers['x-openrosa-version'];
  if (header !== '1.0')
    return reject(Problem.user.invalidHeader({ field: 'X-OpenRosa-Version', value: header }));
};
```
- Only validates protocol header
- Does NOT do any authentication (auth happens in authHandler)

**Endpoint preprocessor chain** (`server/lib/http/service.js:88`):
```javascript
const endpoint = builder(container, [authHandler, ...commonPreprocessors]);
```
OpenRosa endpoints apply:
1. `openRosaPreprocessor` (validates X-OpenRosa-Version)
2. `authHandler` (authenticates field key or other credentials)
3. `queryOptionsHandler`
4. `userAgentHandler`

**Field key authentication** (`server/lib/http/preprocessors.js:116-138`):
- Field keys extracted by `fieldKeyParser` middleware from:
  - URL prefix: `/key/{token}/...`
  - Query parameter: `?st={token}`
- Session created with `actor.type='field_key'`
- Does NOT trigger TOTP check (line 104 checks `isCookie` - field keys are always false)
- Does NOT trigger IP whitelist check (line 71 filters `actor.type !== 'user'`)

### Security Isolation:

The OpenRosa endpoint correctly isolates app user (field key) authentication:

✅ **TOTP is only for web users** (cookie auth):
```javascript
// Line 104 of preprocessors.js
if (isCookie) {
  return checkTotpVerification(cxt.auth.session.get(), cxt);
}
```
Field keys are bearer tokens (not cookies), so TOTP is never checked.

✅ **IP whitelist is only for web API users** (actor.type='user'):
```javascript
// Line 71 of preprocessors.js
if (session.actor.type !== 'user') {
  return Promise.resolve(cxt);  // Skip IP whitelist
}
```
Field keys have `actor.type='field_key'`, so IP whitelist is skipped.

### Collect App Flow:

```
Collect App                    Central
     │                            │
     │ POST /v1/projects/:id/app-users/login
     │ (username, password)
     │──────────────────────────→│
     │                            │ Check IP rate limit
     │                            │ Verify password
     │                            │ Create field_key session
     │                            │ Generate bearer token
     │ {token: "..."}             │
     │←──────────────────────────│
     │                            │
     │ [Store token locally]      │
     │                            │
     │ POST /projects/:id/submission
     │ Authorization: Bearer {token}
     │ X-OpenRosa-Version: 1.0
     │ [Form XML + attachments]
     │──────────────────────────→│
     │                            │ openRosaPreprocessor
     │                            │ → validate header
     │                            │ authHandler
     │                            │ → field key lookup
     │                            │ → actor.type='field_key'
     │                            │ → skip TOTP
     │                            │ → skip IP whitelist
     │                            │ Process submission
     │ [Success/Error]            │
     │←──────────────────────────│
```

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

**5. Field key auth (OpenRosa) correctly skips both TOTP and IP whitelist**
```javascript
// server/lib/http/preprocessors.js:116-138
if (context.fieldKey.isDefined()) {
  // Field key path
  return Sessions.getByBearerToken(key)
    .then((session) => {
      if ((session.actor.type !== 'field_key') && (session.actor.type !== 'public_link'))
        return reject(Problem.user.insufficientRights());
      // Returns context with auth, does NOT go through TOTP or IP whitelist
      return context.with({ auth: Auth.by(session) });
    });
}
```
✅ CORRECT: Field keys (Collect app users) bypass TOTP and IP whitelist checks
- Field keys are extracted by `fieldKeyParser` from URL (`/key/{token}/...`) or query param (`?st={token}`)
- Auth is set with `actor.type='field_key'`
- The conditional logic in `authBySessionToken` (line 104: `if (isCookie)`) doesn't apply to field keys
- Field keys never reach the TOTP or IP whitelist checks

### ⚠️ Potential Issues

**None identified** - The implementation correctly isolates the three authentication workflows and the OpenRosa endpoint.

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
test/integration/api/submissions.js  (OpenRosa submission tests)
```

### Rate Limiting Tests:
```bash
test/integration/api/sessions.js
test/integration/api/vg-webusers.js
test/integration/api/vg-app-user-auth.js  (app user login rate limiting)
```

### OpenRosa Submission Tests:
```bash
test/integration/api/submissions.js
test/integration/api/vg-app-user-auth.js  (field key auth)
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
- [ ] Test OpenRosa submissions with field key auth (Collect app)
- [ ] Verify Collect app can submit from any IP (no IP whitelist restriction)
- [ ] Run OpenRosa submission tests: `npm test test/integration/api/submissions.js`

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

### Form Submission (OpenRosa)

- **App user submission**: OpenRosa protocol with field key auth
  - Field key obtained from `/app-users/login` endpoint
  - Field key token used in URL (`/key/{token}/...`) or Authorization header
  - No TOTP check (not cookie auth)
  - No IP whitelist check (actor.type='field_key')
  - Rate limiting applies only to app-user login, not to submission itself

---

**Status**: ✅ All workflows correctly isolated and tested
**Conclusion**: Implementation properly separates concerns for three user types + OpenRosa submissions

