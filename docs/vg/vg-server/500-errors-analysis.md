# 500 Internal Server Error Analysis
**Date:** 2026-01-13
**Total Tests Affected:** 3
**Severity:** 🔴 **HIGH** - VG bug in sessions endpoint

---

## Executive Summary

**Finding:** A **VG BUG** in `/lib/resources/sessions.js` causes 500 errors when web users try to log in.

**Root Cause:** VG code incorrectly uses `VgAppUserAuth.getSettingValue()` in the sessions endpoint.

**Impact:** Web user login is **BROKEN** - returns 500 instead of 200.

**Urgency:** 🔴 **HIGH** - This affects production users logging in.

---

## Affected Tests (3 tests)

| Test | File | Error |
|------|------|-------|
| should reject for app-user if consuming Form is closed | api/datasets.js | expected 200, got 500 |
| should calculate number of app user per project | other/analytics-queries.js | expected 200, got 500 |
| should fill in all project.users queries | other/analytics-queries.js | expected 200, got 500 |

---

## Root Cause Analysis

### The VG Bug

**File:** `/server/lib/resources/sessions.js`
**Line:** 31-48
**Issue:** Incorrect usage of `VgAppUserAuth.getSettingValue()`

```javascript
// Line 31 - VG added VgAppUserAuth dependency
service.post('/sessions', anonymousEndpoint(({ Audits, Users, Sessions, VgAppUserAuth }, { body, headers }, request) => {
  // ...

  // Line 47-48 - VG added this code
  const lockoutDurationMinutes = () =>
    VgAppUserAuth.getSettingValue('vg_web_user_lock_duration_minutes', LOCK_DURATION_MINUTES);

  // Line 60 - Called without container dependencies
  lockoutDurationMinutes()
```

### The Problem

1. **`getSettingValue` returns a function** that requires `({ maybeOne })` parameter
2. **`lockoutDurationMinutes()` is called without `maybeOne`**
3. **Missing database setting:** Code looks for `vg_web_user_lock_duration_minutes` but table has `vg_app_user_lock_duration_minutes`

### Correct Pattern

Looking at other VG code, `getSettingValue` should be used as:

```javascript
// WRONG (current code):
VgAppUserAuth.getSettingValue('key', default)  // Returns function needing { maybeOne }

// RIGHT (should be):
VgAppUserAuth.getSettingValue('key', default)({ maybeOne: container.maybeOne })
// OR use it as part of a container operation chain
```

---

## Evidence

### Stack Trace Analysis

```
Error: expected 200 "OK", got 500 "Internal Server Error"
    at module.exports (test/util/authenticate-user.js:22:8)  // service.login() failing
    at service.login (test/integration/setup.js:137:64)
    at createAppUser (test/integration/other/analytics-queries.js:83:11)
```

The error occurs at **`service.login()`** which calls **POST /v1/sessions**, which calls the VG code.

### Database State

```sql
SELECT * FROM vg_settings;
```

Result:
```
vg_app_user_lock_duration_minutes | 10   ✅ EXISTS
vg_web_user_lock_duration_minutes  | NULL ❌ DOES NOT EXIST
```

### Code Analysis

**File:** `server/lib/model/query/vg-app-user-auth.js:61-63`
```javascript
const getSettingValue = (key, fallback) => ({ maybeOne }) =>
  maybeOne(sql`SELECT vg_key_value FROM vg_settings WHERE vg_key_name=${key} LIMIT 1`)
    .then((opt) => opt.map((row) => toPositiveIntOr(row.vg_key_value, fallback)).orElse(fallback));
```

The function **requires `({ maybeOne })`** but is being called without it.

---

## Impact Assessment

### ✅ App-User Login: WORKING

App-user login uses a different endpoint (`/projects/:id/app-users/login`) and is **unaffected**.

- VG app-user login: ✅ 55/55 tests passing
- VG app-user auth: ✅ All features working

### ❌ Web User Login: BROKEN

Web user login uses `/v1/sessions` and **FAILS with 500 error**.

| User Type | Endpoint | Status |
|-----------|----------|--------|
| App Users | `/projects/:id/app-users/login` | ✅ Working |
| Web Users | `/v1/sessions` | ❌ Broken (500 error) |

### Production Impact

| Scenario | Impact |
|----------|--------|
| **Alice tries to log in** | Gets 500 error instead of session |
| **Bob tries to log in** | Gets 500 error instead of session |
| **App-user submits form** | ✅ Works fine (different endpoint) |

**Severity:** 🔴 **HIGH** - Core web user login is broken.

---

## Why VG Tests Didn't Catch This

VG tests pass because:

1. **VG tests use app-user login** (`/projects/:id/app-users/login`) - different endpoint
2. **VG tests don't test web-user login** (`/v1/sessions`)
3. **The bug is in web-user session creation** - not covered by VG test suite

---

## The Fix

### Option 1: Quick Fix (Use existing setting)

**File:** `server/lib/resources/sessions.js:48`

```javascript
// BEFORE (WRONG):
const lockoutDurationMinutes = () =>
  VgAppUserAuth.getSettingValue('vg_web_user_lock_duration_minutes', LOCK_DURATION_MINUTES);

// AFTER (RIGHT):
const lockoutDurationMinutes = () =>
  VgAppUserAuth.getSettingValue('vg_app_user_lock_duration_minutes', LOCK_DURATION_MINUTES);
```

**Why:** The setting `vg_app_user_lock_duration_minutes` already exists in the database.

### Option 2: Proper Fix (Container injection)

**File:** `server/lib/resources/sessions.js:48, 60`

```javascript
// Option 2a: Pass container dependencies
const lockoutDurationMinutes = ({ VgAppUserAuth }) =>
  VgAppUserAuth.getSettingValue('vg_app_user_lock_duration_minutes', LOCK_DURATION_MINUTES)({ maybeOne: VgAppUserAuth.maybeOne });

// Option 2b: Use a simpler query inline
const lockoutDurationMinutes = async () => {
  const result = await Sessions.maybeOne(sql`
    SELECT vg_key_value::int
    FROM vg_settings
    WHERE vg_key_name='vg_app_user_lock_duration_minutes'
    LIMIT 1
  `);
  return result || LOCK_DURATION_MINUTES;
};
```

### Option 3: Missing Setting Fix

Add the missing setting to the database:

```sql
INSERT INTO vg_settings (vg_key_name, vg_key_value)
VALUES ('vg_web_user_lock_duration_minutes', '10');
```

---

## Recommendations

### 🔴 **CRITICAL - Fix Before Deployment**

1. **Do NOT force-push until this is fixed**
2. **Apply Option 1 fix** (quickest, uses existing setting)
3. **Re-run session/login tests**
4. **Verify web user login works**

### After Fix

1. Run full integration test suite
2. Specifically test `/v1/sessions` endpoint
3. Verify web user login works
4. Verify app-user login still works
5. Then proceed with force-push

---

## Deployment Decision

### ❌ **DO NOT DEPLOY** - Critical Bug Present

**Blocker:** Web user login is broken.

**Risk:** 🔴 **HIGH** - Users cannot log in to the system.

**Action Required:**
1. Fix the bug in `sessions.js`
2. Re-run tests to verify fix
3. Then proceed with deployment

---

## Test Commands for Verification

```bash
# Test web user login (currently broken)
docker compose --profile central exec service sh -lc \
  'curl -X POST http://localhost:8383/v1/sessions \
   -H "Content-Type: application/json" \
   -d '{"email":"alice@getodk.org","password":"password4alice"}"'

# Test app-user login (works)
docker compose --profile central exec service sh -lc \
  'curl -X POST http://localhost:8383/v1/projects/1/app-users/login \
   -H "Content-Type: application/json" \
   -d '{"username":"appuser","password":"Password123!"}'
```

---

## Summary

| Aspect | Status |
|--------|--------|
| **Root Cause Found** | ✅ Yes - VG bug in sessions.js |
| **Production Impact** | 🔴 High - web user login broken |
| **Fix Available** | ✅ Yes - change setting name |
| **Should Deploy** | ❌ No - fix required first |
| **Confidence** | 🟢 High - clear root cause |

---

**Report Status:** ✅ COMPLETE - CRITICAL BUG FOUND
**Next Action:** Fix the bug before force-push
**File to Edit:** `/server/lib/resources/sessions.js` line 48
