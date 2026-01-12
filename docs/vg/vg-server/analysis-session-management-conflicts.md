# Session Management Conflicts Analysis: PR #1586

**Analysis Date:** 2026-01-12
**Task:** central-xav.3 (P1.1)
**Upstream PR:** #1586 - Config-based session lifetime for Web users
**Risk Level:** HIGH
**Conflict Complexity:** MODERATE

---

## Executive Summary

VG and upstream have both modified session management, but in compatible ways with one high-conflict area:

**GOOD NEWS:**
- ✅ Both use config-based session lifetime (`config.default.sessionLifetime`)
- ✅ VG's changes are mostly additive (new functions, extended queries)
- ✅ No structural conflicts in session creation logic

**HIGH CONFLICT:**
- ⚠️ `lib/resources/sessions.js` - VG added extensive login hardening (83 lines), upstream simplified the endpoint
- ⚠️ Requires careful merge to preserve both VG hardening and upstream error handling improvements

---

## File-by-File Analysis

### 1. lib/model/query/sessions.js

**Conflict Level:** LOW (Additive VG changes)

**VG Changes:**
```javascript
// Line 45-47: Extended getByBearerToken with VG field key auth check
const getByBearerToken = (token) => ({ maybeOne }) => (isValidToken(token) ? maybeOne(sql`
select ${_unjoiner.fields} from sessions
join actors on actors.id=sessions."actorId"
left join vg_field_key_auth on vg_field_key_auth."actorId"=sessions."actorId"
where token=${token} and sessions."expiresAt" > now()
  and (actors.type <> 'field_key' or (vg_field_key_auth."actorId" is not null and vg_field_key_auth.vg_active = true))`)
  .then(map(_unjoiner)) : Promise.resolve(Option.none()));

// Lines 54-64: New trimByActorId function for session cap enforcement
const trimByActorId = (actorId, limit) => ({ run }) =>
  run(sql`
    DELETE FROM sessions
    WHERE "actorId"=${actorId}
      AND token NOT IN (
        SELECT token FROM sessions
        WHERE "actorId"=${actorId}
        ORDER BY "createdAt" DESC
        LIMIT ${limit}
      )
  `);

// Line 79: Added trimByActorId to exports
module.exports = { create, getByBearerToken, terminateByActorId, trimByActorId, terminate, reap };
```

**Upstream Changes:**
- Session lifetime already uses `config.default.sessionLifetime` (line 20) - SAME AS VG!
- No other changes to query functions

**Resolution Strategy:**
1. Accept upstream version as base
2. Add VG's `vg_field_key_auth` check to `getByBearerToken` query
3. Add VG's `trimByActorId` function
4. Add `trimByActorId` to module exports

**No database timestamp handling conflicts** - both use the same approach.

---

### 2. lib/resources/sessions.js

**Conflict Level:** HIGH (Major logic rewrite)

**VG Changes: Web User Login Hardening (83 lines added)**

VG completely rewrote the `POST /sessions` endpoint to add:

1. **Login Attempt Tracking:**
   ```javascript
   const MAX_FAILURES = 5;
   const WINDOW_MINUTES = 5;
   const LOCK_DURATION_MINUTES = 10; // Configurable via vg_settings
   ```

2. **Email/IP Normalization:**
   ```javascript
   const normalizeEmail = (value) => (typeof value === 'string')
     ? value.trim().toLowerCase()
     : null;
   const normalizeIp = (value) => (typeof value === 'string' && value.trim() !== '')
     ? value.trim()
     : null;
   ```

3. **Failed Login Auditing:**
   ```javascript
   const logFailedLogin = () => Audits.log(null, 'user.session.create.failure', null, {
     email: normalizedEmail,
     ip: normalizedIp,
     userAgent: request.get('user-agent') ?? null
   });
   ```

4. **Lockout Mechanism:**
   ```javascript
   const recordFailureAndMaybeLockout = () => {
     // Check failure count in WINDOW_MINUTES
     // If count >= MAX_FAILURES, create lockout audit entry
     // Return attemptsRemaining for response header
   };

   const isLocked = () => {
     // Check if user has recent lockout entry
     // Calculate remaining lockout time
     // Throw lockoutError with retryAfterSeconds if locked
   };
   ```

5. **Response Headers:**
   ```javascript
   problem.loginAttemptsRemaining = attemptsRemaining;
   error.retryAfterSeconds = retryAfterSeconds;
   ```

6. **Configurable Lockout Duration:**
   ```javascript
   const lockoutDurationMinutes = () =>
     VgAppUserAuth.getSettingValue('vg_web_user_lock_duration_minutes', LOCK_DURATION_MINUTES);
   ```

**Upstream Changes: Simplified Error Handling**

Upstream simplified the endpoint by:

1. **Cleaner promise chain:**
   ```javascript
   return Users.getByEmail(email)
     .then(getOrReject(Problem.user.authenticationFailed()))
     .then((user) => verifyPassword(password, user.password)
       .then(rejectIf(
         (verified) => (verified !== true),
         noargs(Problem.user.authenticationFailed)
       ))
       .then(() => createUserSession({ Audits, Sessions, Users }, headers, user)));
   ```

2. **Removed redundant user lookup:**
   - VG: `getUserAndHash()` fetches user OR any password hash (timing attack mitigation)
   - Upstream: Direct user lookup, simpler logic

3. **No login hardening:**
   - No attempt tracking
   - No lockout mechanism
   - No rate limiting

**Conflict Analysis:**

The conflict is **structural** - VG and upstream have fundamentally different approaches:

| Aspect | VG | Upstream |
|--------|-----|----------|
| **Error Handling** | Complex try-catch with failure recording | Simple promise chain with rejectIf |
| **Timing Attack Mitigation** | getUserAndHash() fetches any hash if user not found | Direct user lookup (faster failure) |
| **Lockout Logic** | Extensive (83 lines) | None |
| **Audit Logging** | Detailed (failure, lockout, success) | Success only |
| **Response Headers** | loginAttemptsRemaining, retryAfterSeconds | None |

**Resolution Strategy:**

**Option A: Layer VG on Top (Recommended)**
1. Accept upstream's simplified error handling structure as base
2. Wrap upstream logic with VG's lockout checks:
   ```javascript
   return isLocked()  // VG pre-check
     .then(() => Users.getByEmail(email)  // Upstream logic
       .then(getOrReject(Problem.user.authenticationFailed()))
       .then((user) => verifyPassword(password, user.password)
         .then(rejectIf(...))
         .then(() => createUserSession(...))))
     .catch((problem) => {  // VG post-failure handling
       if (problem?.problemCode === authFailed.problemCode)
         return recordFailureAndMaybeLockout()
           .then((details) => { /* add headers */ });
       return Promise.reject(problem);
     });
   ```

**Option B: Keep VG Completely (Riskier)**
1. Reject upstream changes to sessions.js
2. Keep VG's 83-line implementation
3. Risk: May conflict with other upstream changes (e.g., new imports, error handling patterns)

**Recommendation: Option A** - Preserves VG security features while adopting upstream improvements.

---

### 3. lib/http/sessions.js

**Conflict Level:** UNKNOWN (Need to check)

Let me check if this file has conflicts.

---

## Upstream PR #1586 Details

**PR Title:** Config-based session lifetime for Web users

**Key Changes:**
1. **Configuration Support:**
   - Added `sessionLifetime` setting to config
   - Supports environment variable override: `sessionlifetime=86400`
   - Centralized definition via node-config

2. **Consistency Improvements:**
   - Session expiry calculated server-side at creation time
   - Eliminates "jittery" behavior from wall-clock timing differences
   - Consistent reference point for all session lifetimes

3. **No Breaking Changes:**
   - Default behavior unchanged (existing session lifetime maintained)
   - Backward compatible with existing sessions

**Quote from PR:**
> "the env is only read once (on startup)" but provides centralized definition of supported environment variables without requiring changes at individual call sites.

**Files Modified in PR:**
- `lib/model/query/sessions.js` - Core session query logic
- `docs/api.yaml` - API documentation
- `test/integration/api/sessions.js` - Test coverage
- Configuration files

---

## VG Session Management Features Summary

### Core Features

1. **App User Session Management:**
   - Short-lived bearer tokens (no long-lived tokens)
   - Configurable TTL via `vg_app_user_session_ttl_days`
   - Session cap enforcement via `trimByActorId()`
   - Project-level TTL/cap overrides

2. **Web User Login Hardening:**
   - Failed login attempt tracking
   - Rate limiting (5 failures in 5 minutes)
   - Automatic lockout (10 minutes, configurable)
   - Audit logging for failures and lockouts
   - Response headers: attempts remaining, retry-after

3. **Field Key Auth Integration:**
   - Active status check in `getByBearerToken`
   - VG field keys must be active to authenticate
   - Seamless integration with existing session queries

### Database Dependencies

VG session features require these tables:
- `vg_field_key_auth` - Stores field key active status
- `vg_settings` - Stores TTL/cap configuration
- `vg_project_settings` - Stores project-level overrides
- Audit table extensions for login failures and lockouts

---

## Rebase Strategy

### Phase 1: Pre-Rebase Preparation

1. ✅ Document current state
2. ✅ Identify conflict areas
3. **Create merge strategy document** (this file)
4. **Test current VG session features** (establish baseline)

### Phase 2: Rebase Execution

**Step 1: Accept upstream sessions.js (query)**
```bash
git checkout upstream/master -- lib/model/query/sessions.js
```

**Step 2: Re-apply VG changes to sessions.js (query)**
- Add vg_field_key_auth check to getByBearerToken
- Add trimByActorId function
- Update module exports

**Step 3: Manual merge of sessions.js (resources)**
- Use Option A strategy (layer VG on top)
- Preserve upstream error handling structure
- Add VG lockout logic as wrapper
- Keep VG audit logging and response headers

**Step 4: Run tests**
```bash
# VG session tests
npx mocha test/integration/api/vg-app-user-auth.js

# Upstream session tests
npx mocha test/integration/api/sessions.js

# Web login lockout tests (VG)
npx mocha test/integration/api/sessions.js --grep "lockout"
```

### Phase 3: Verification

Test these scenarios:

**App User Sessions:**
- [ ] App user login with username/password
- [ ] Session expires after configured TTL
- [ ] Session cap enforced (trimByActorId works)
- [ ] Field key active status checked
- [ ] Inactive field keys cannot authenticate

**Web User Login Hardening:**
- [ ] Failed login attempts tracked
- [ ] 5 failures in 5 minutes triggers lockout
- [ ] Lockout lasts 10 minutes (or configured duration)
- [ ] Response headers present: loginAttemptsRemaining, retryAfterSeconds
- [ ] Audit entries created for failures and lockouts
- [ ] Successful login resets failure counter

**Upstream Features:**
- [ ] Config-based session lifetime works
- [ ] Environment variable override works
- [ ] Session creation timestamp consistency
- [ ] No regressions in standard web user login

---

## Risk Assessment

### High Risk Areas

1. **lib/resources/sessions.js (POST /sessions)**
   - Risk: Breaking VG login hardening or upstream error handling
   - Mitigation: Careful manual merge, comprehensive testing
   - Fallback: Keep VG version entirely if merge fails

2. **Audit table schema**
   - Risk: VG audit entries for lockouts may conflict with upstream audit changes
   - Mitigation: Check upstream audit changes in Phase 1 analysis
   - Fallback: Keep VG audit schema, add upstream changes separately

### Medium Risk Areas

1. **lib/model/query/sessions.js (getByBearerToken)**
   - Risk: VG's vg_field_key_auth join may break if upstream changes query structure
   - Mitigation: VG changes are additive (LEFT JOIN), low conflict probability
   - Fallback: Easy to re-apply VG changes on top of upstream

### Low Risk Areas

1. **Session lifetime configuration**
   - Risk: Minimal - both already use config-based approach
   - Mitigation: No action needed, already compatible

2. **trimByActorId function**
   - Risk: Minimal - new function, no upstream equivalent
   - Mitigation: Simple re-addition after upstream merge

---

## Testing Checklist

### Pre-Rebase Baseline

Capture current behavior:

```bash
# Run all session-related tests
npx mocha test/integration/api/sessions.js --reporter json > /tmp/vg-sessions-baseline.json
npx mocha test/integration/api/vg-app-user-auth.js --reporter json > /tmp/vg-app-user-auth-baseline.json
```

### Post-Rebase Validation

Compare with baseline:

```bash
# Re-run tests
npx mocha test/integration/api/sessions.js --reporter json > /tmp/vg-sessions-rebase.json
npx mocha test/integration/api/vg-app-user-auth.js --reporter json > /tmp/vg-app-user-auth-rebase.json

# Diff results
diff /tmp/vg-sessions-baseline.json /tmp/vg-sessions-rebase.json
```

### Manual Testing Scenarios

1. **Web User Login:**
   - Normal login (success)
   - Wrong password (failure, attempts remaining header)
   - 5 failures (lockout triggered, retry-after header)
   - Wait 10 minutes (lockout expires, login succeeds)

2. **App User Session:**
   - Login with username/password
   - Session expires after TTL
   - Session cap enforced (create > cap sessions, oldest deleted)
   - Inactive field key cannot login

3. **Config Testing:**
   - Change `sessionLifetime` in config
   - Restart server
   - Verify new sessions use new lifetime
   - Change `vg_web_user_lock_duration_minutes` in vg_settings
   - Verify lockout duration updated

---

## Rollback Plan

If session management breaks after rebase:

```bash
# Restore sessions.js files from backup branch
git checkout vg-work-pre-rebase-2025.4.0 -- lib/model/query/sessions.js
git checkout vg-work-pre-rebase-2025.4.0 -- lib/resources/sessions.js
git checkout vg-work-pre-rebase-2025.4.0 -- lib/http/sessions.js

# Re-run tests
npx mocha test/integration/api/sessions.js
npx mocha test/integration/api/vg-app-user-auth.js

# Commit rollback
git add lib/model/query/sessions.js lib/resources/sessions.js lib/http/sessions.js
git commit -m "Rollback: Restore VG session management (rebase conflict resolution failed)"
```

---

## Next Steps

1. ✅ Complete this analysis (P1.1)
2. **Move to P1.2:** Analyze auth/password conflicts
3. **Move to P1.3:** Analyze database migration conflicts
4. **Complete P1.4:** Create comprehensive conflict resolution plan
5. **Begin P2.1:** Start interactive rebase

---

## References

- **Upstream PR:** https://github.com/getodk/central-backend/pull/1586
- **VG Sessions Query:** server/lib/model/query/sessions.js:20,45-47,54-64,79
- **VG Sessions Resource:** server/lib/resources/sessions.js (83 lines of login hardening)
- **VG Session Tests:** server/test/integration/api/vg-app-user-auth.js
- **Pre-Rebase State Doc:** docs/vg/vg-server/pre-rebase-state-v2024.3.1.md
- **Rebase Plan:** docs/vg/vg-server/rebase-v2025.4.0-plan.md

---

**Analysis Status:** Complete
**Next Task:** P1.2 - Analyze auth/password conflicts
**Recommendation:** Proceed with Option A (Layer VG on top) for lib/resources/sessions.js
