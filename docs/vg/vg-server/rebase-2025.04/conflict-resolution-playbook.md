# Conflict Resolution Playbook: v2024.3.1 → v2025.4.0

**Plan Date:** 2026-01-12
**Task:** central-xav.6 (P1.4)
**Status:** Ready for Phase 2 Execution
**Based on:** Analysis docs P1.1, P1.2, P1.3

---

## Executive Summary

This playbook provides step-by-step instructions for resolving all conflicts during the server rebase from v2024.3.1 to v2025.4.0.

**Conflict Areas Identified:**
1. ⚠️ **Session Management** (HIGH RISK) - Major code restructuring
2. ✅ **Auth/Password** (LOW RISK) - Minor enhancement needed
3. ⚠️ **Database Migrations** (MEDIUM RISK) - Different approaches, no overlap
4. ✅ **App-Users Endpoints** (LOW RISK) - Additive VG changes
5. ✅ **Other Files** (LOW RISK) - Standard conflict resolution

**Overall Risk:** MEDIUM-HIGH (manageable with careful execution)

**Estimated Time:** 2-4 hours for Phase 2 execution

---

## Pre-Rebase Checklist

Before starting Phase 2, ensure:

- [x] Backup branch created: `vg-work-pre-rebase-2025.4.0`
- [x] Pre-rebase state documented
- [x] All analyses complete (P1.1, P1.2, P1.3)
- [ ] This playbook reviewed and understood
- [ ] Test database available
- [ ] Docker environment running
- [ ] No uncommitted changes in server/

---

## Phase 2: Rebase Execution

### P2.1: Start Interactive Rebase

**Task:** central-xav.7

**Commands:**
```bash
cd server
git fetch upstream master
git rebase -i upstream/master
```

**What to Expect:**
- Git will open an editor with 358 VG commits
- **DO NOT SQUASH OR DROP ANY COMMITS**
- Leave all commits as "pick"
- Save and close editor

**Rebase Will Stop At:** First conflict (likely in `lib/resources/sessions.js`)

**If Rebase Starts Clean:**
Proceed to P2.2 when conflicts appear.

**Rollback Trigger:**
- If git rebase fails to start
- If unexpected errors occur

**Rollback Command:**
```bash
git rebase --abort
git checkout vg-work
```

---

### P2.2: Resolve Session Management Conflicts

**Task:** central-xav.8
**Risk Level:** HIGH
**Reference:** `analysis-session-management-conflicts.md`

#### Expected Conflicts

**File 1: lib/model/query/sessions.js**

**Conflict:** VG's `trimByActorId` function and `vg_field_key_auth` check

**Resolution Strategy:**
1. Accept upstream version as base
2. Re-add VG additions

**Commands:**
```bash
# Check conflict status
git status

# View conflict
git diff lib/model/query/sessions.js
```

**Manual Merge:**

Open `lib/model/query/sessions.js` and ensure it has:

1. **Line 45-48:** VG's active field key check
```javascript
const getByBearerToken = (token) => ({ maybeOne }) => (isValidToken(token) ? maybeOne(sql`
select ${_unjoiner.fields} from sessions
join actors on actors.id=sessions."actorId"
left join vg_field_key_auth on vg_field_key_auth."actorId"=sessions."actorId"
where token=${token} and sessions."expiresAt" > now()
  and (actors.type <> 'field_key' or (vg_field_key_auth."actorId" is not null and vg_field_key_auth.vg_active = true))`)
  .then(map(_unjoiner)) : Promise.resolve(Option.none()));
```

2. **Lines 54-64:** VG's trimByActorId function
```javascript
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
```

3. **Line 79:** Add to exports
```javascript
module.exports = { create, getByBearerToken, terminateByActorId, trimByActorId, terminate, reap };
```

**Mark Resolved:**
```bash
git add lib/model/query/sessions.js
```

**File 2: lib/resources/sessions.js**

**Conflict:** VG's 83-line login hardening vs upstream's simplified error handling

**Resolution Strategy:** Layer VG on top (Option A from analysis)

**Manual Merge Steps:**

1. Accept upstream's base structure (simplified promise chain)
2. Wrap with VG's lockout checks

**Target Structure:**
```javascript
service.post('/sessions', anonymousEndpoint(({ Audits, Users, Sessions, VgAppUserAuth }, { body, headers }, request) => {
  // VG: Constants and helpers
  const MAX_FAILURES = 5;
  const WINDOW_MINUTES = 5;
  const LOCK_DURATION_MINUTES = 10;
  const normalizeEmail = (value) => (typeof value === 'string') ? value.trim().toLowerCase() : null;
  const normalizeIp = (value) => (typeof value === 'string' && value.trim() !== '') ? value.trim() : null;

  const { email, password } = body;
  const authFailed = Problem.user.authenticationFailed();
  const normalizedEmail = normalizeEmail(email);
  const normalizedIp = normalizeIp(request.ip);

  // VG: Audit logging helper
  const logFailedLogin = () => Audits.log(null, 'user.session.create.failure', null, {
    email: normalizedEmail,
    ip: normalizedIp,
    userAgent: request.get('user-agent') ?? null
  });

  // VG: Lockout helpers
  const lockoutDurationMinutes = () =>
    VgAppUserAuth.getSettingValue('vg_web_user_lock_duration_minutes', LOCK_DURATION_MINUTES);

  const lockoutError = (retryAfterSeconds) => {
    const error = Problem.user.authenticationFailed();
    error.retryAfterSeconds = retryAfterSeconds;
    error.loginAttemptsRemaining = 0;
    return error;
  };

  const recordFailureAndMaybeLockout = () => {
    if (normalizedEmail == null) return logFailedLogin();
    return logFailedLogin()
      .then(() => Promise.all([
        Audits.getWebLoginFailureCount(normalizedEmail, normalizedIp, WINDOW_MINUTES),
        lockoutDurationMinutes()
      ]))
      .then(([count, durationMinutes]) =>
        Audits.hasRecentWebLoginLockout(normalizedEmail, normalizedIp, durationMinutes)
          .then((isLocked) => ({ count, isLocked, durationMinutes })))
      .then(({ count, isLocked, durationMinutes }) => {
        const attemptsRemaining = Math.max(MAX_FAILURES - count, 0);
        if (!isLocked && count >= MAX_FAILURES)
          return Audits.log(null, 'user.session.lockout', null, {
            email: normalizedEmail,
            ip: normalizedIp,
            durationMinutes
          }).then(() => ({ attemptsRemaining: 0 }));
        return { attemptsRemaining };
      });
  };

  const isLocked = () => (normalizedEmail == null)
    ? Promise.resolve(false)
    : lockoutDurationMinutes()
      .then((durationMinutes) =>
        Audits.getLatestWebLoginLockoutAt(normalizedEmail, normalizedIp)
          .then((lockedAt) => {
            if (lockedAt == null) return false;
            const remainingMs = new Date(lockedAt).getTime() + (durationMinutes * 60 * 1000) - Date.now();
            if (remainingMs <= 0) return false;
            throw lockoutError(Math.ceil(remainingMs / 1000));
          }));

  // Validation
  if (isBlank(email) || isBlank(password))
    return Problem.user.missingParameters({ expected: [ 'email', 'password' ], got: { email, password } });

  // VG: Wrap upstream logic with lockout checks
  return isLocked()
    .then(() => Users.getByEmail(email)  // Upstream logic
      .then(getOrReject(Problem.user.authenticationFailed()))
      .then((user) => verifyPassword(password, user.password)
        .then(rejectIf(
          (verified) => (verified !== true),
          noargs(Problem.user.authenticationFailed)
        ))
        .then(() => createUserSession({ Audits, Sessions, Users }, headers, user))))
    .catch((problem) => {  // VG: Post-failure handling
      if (problem?.problemCode === authFailed.problemCode)
        return recordFailureAndMaybeLockout()
          .then((details) => {
            if (details?.attemptsRemaining != null)
              problem.loginAttemptsRemaining = details.attemptsRemaining;
            return Promise.reject(problem);
          });
      return Promise.reject(problem);
    });
}));
```

**Key Points:**
- Keep upstream's `getOrReject` and `rejectIf` pattern
- Add VG's `isLocked()` pre-check
- Add VG's `recordFailureAndMaybeLockout()` error handling
- Preserve VG's audit logging and response headers

**Mark Resolved:**
```bash
git add lib/resources/sessions.js
```

**File 3: lib/model/query/users.js**

**Conflict:** Upstream removed `getAnyPasswordHash()`, VG needs it

**Resolution:**
```bash
# Accept upstream version
git checkout upstream/master -- lib/model/query/users.js

# Then manually re-add VG's getAnyPasswordHash function
```

**Edit `lib/model/query/users.js`:**

Add before the `module.exports` line:

```javascript
const getAnyPasswordHash = () => ({ maybeOne }) =>
  maybeOne(sql`
    select users.password
    from users
    join actors on users."actorId"=actors.id
    where users.password is not null
      and actors."deletedAt" is null
    limit 1
  `).then((opt) => opt.map((row) => row.password).orNull());
```

Update exports:
```javascript
module.exports = {
  create, update,
  updatePassword, invalidatePassword, provisionPasswordResetToken,
  getAll, getByEmail, getByActorId,
  emailEverExisted, updateLastLoginAt, getAnyPasswordHash  // Add this
};
```

**Mark Resolved:**
```bash
git add lib/model/query/users.js
```

**Continue Rebase:**
```bash
git rebase --continue
```

**Test After Resolution:**
```bash
# Quick syntax check
node -c lib/model/query/sessions.js
node -c lib/resources/sessions.js
node -c lib/model/query/users.js
```

**Rollback Trigger:**
- If syntax errors occur
- If rebase conflicts are too complex to resolve

**Rollback:**
```bash
git rebase --abort
cd ..
git reset --hard vg-work-pre-rebase-2025.4.0
```

---

### P2.3: Resolve Auth/Password Conflicts

**Task:** central-xav.9
**Risk Level:** LOW
**Reference:** `analysis-auth-password-conflicts.md`

#### Expected Conflicts

**Likely:** NONE (VG hasn't modified core auth files)

**If Conflicts Occur:**

**File: lib/util/crypto.js**
```bash
# Accept upstream version (VG hasn't modified this)
git checkout upstream/master -- lib/util/crypto.js
git add lib/util/crypto.js
```

**Enhancement: Update VG Password Policy**

After rebase completes, add 72-byte check:

**Edit `lib/util/vg-password.js`:**
```javascript
const validateVgPassword = (password) => {
  if (typeof password !== 'string') return false;
  if (password.length > 72) return false;  // NEW: Align with upstream bcrypt limit
  return password.length >= policy.minLength
    && policy.special.test(password)
    && policy.upper.test(password)
    && policy.lower.test(password)
    && policy.digit.test(password);
};
```

**Commit Enhancement:**
```bash
git add lib/util/vg-password.js
git commit -m "Enhance: VG password policy 72-byte limit (align with upstream bcrypt)"
```

**Continue Rebase:**
```bash
git rebase --continue
```

---

### P2.4: Resolve App-Users Endpoint Conflicts

**Task:** central-xav.10
**Risk Level:** LOW
**Reference:** `pre-rebase-state-v2024.3.1.md`

#### Expected Conflicts

**Likely:** NONE (VG endpoints are additive in `vg-app-user-auth.js`)

**If Conflicts in `lib/resources/app-users.js`:**

**Strategy:** Keep both VG and upstream endpoints

```bash
# View conflict
git diff lib/resources/app-users.js

# Manual merge: ensure both sets of endpoints present
# - Upstream: attachment upload
# - VG: login, password reset/change, revoke, activate
```

**Verification:**
```bash
# Check for VG endpoints in app-users.js
grep -E "(login|password|revoke|active)" lib/resources/app-users.js

# Should find VG endpoint definitions
```

**Mark Resolved:**
```bash
git add lib/resources/app-users.js
git rebase --continue
```

---

### P2.5: Resolve Migration Conflicts

**Task:** central-xav.11
**Risk Level:** MEDIUM
**Reference:** `analysis-database-migration-conflicts.md`

#### Expected Conflicts

**Likely:** NONE (VG doesn't modify `lib/model/migrations/`)

**Action:** Accept all upstream migration files

```bash
# If conflicts in migrations directory
git checkout upstream/master -- lib/model/migrations/
git add lib/model/migrations/
git rebase --continue
```

**No Code Conflicts Expected** - Different file paths:
- Upstream: `lib/model/migrations/*.js`
- VG: `docs/sql/vg_app_user_auth.sql`

---

### P2.6: Resolve Remaining Conflicts and Complete Rebase

**Task:** central-xav.12
**Depends on:** P2.2, P2.3, P2.4, P2.5
**Risk Level:** LOW-MEDIUM

#### General Conflict Resolution Strategy

For any remaining conflicts:

**1. VG-Only Files (Keep VG Version)**
```bash
# Files starting with vg-*
git checkout --ours lib/domain/vg-*.js
git checkout --ours lib/model/query/vg-*.js
git checkout --ours lib/resources/vg-*.js
git checkout --ours test/integration/api/vg-*.js

git add lib/domain/vg-*.js
git add lib/model/query/vg-*.js
git add lib/resources/vg-*.js
git add test/integration/api/vg-*.js
```

**2. Upstream-Only Files (Accept Upstream)**
```bash
# Files VG hasn't modified
git checkout upstream/master -- <file>
git add <file>
```

**3. Mixed Files (Manual Merge)**
```bash
# Open in editor, resolve conflicts
# Keep both VG and upstream changes where possible
# Test after resolution
```

**Common Conflict Patterns:**

**Pattern A: Import statements**
```javascript
// KEEP BOTH
const { something } = require('./upstream-module');  // Upstream
const { vgThing } = require('./vg-module');  // VG
```

**Pattern B: Function additions**
```javascript
// KEEP BOTH
const upstreamFunction = () => { /* upstream code */ };  // Upstream
const vgFunction = () => { /* VG code */ };  // VG
```

**Pattern C: Exports**
```javascript
// MERGE
module.exports = {
  upstreamFunction,  // Upstream
  vgFunction  // VG - add to exports
};
```

**Complete Rebase:**
```bash
# When all conflicts resolved
git rebase --continue

# If no more conflicts, rebase is complete
```

**Verify Rebase Success:**
```bash
# Check branch status
git status
# Should show: "Your branch and 'origin/vg-work' have diverged"

# Check commit count
git log --oneline -10
# Should show recent VG commits on top of upstream commits

# Check upstream merge base
git merge-base HEAD upstream/master
# Should be the tip of upstream/master
```

**Post-Rebase Commit Message:**

If git prompts for final rebase message:
```
Rebase: VG server v2024.3.1 → upstream v2025.4.0

Integrated 274 upstream commits:
- Config-based session lifetime (PR #1586)
- Password validation enhancements (72-byte limit)
- 44 new database migrations
- Entity features, geometry API, submission event stamping

Preserved 358 VG commits:
- App user authentication system
- Web user login hardening
- Session TTL/cap enforcement
- VG database schema (7 tables)
- Enketo status monitoring
- Telemetry system

Conflict resolutions:
- lib/resources/sessions.js: Layered VG login hardening on upstream error handling
- lib/model/query/sessions.js: Re-added VG trimByActorId and field key check
- lib/model/query/users.js: Re-added VG getAnyPasswordHash for timing attack mitigation

Epic: central-xav | Issue: https://github.com/drguptavivek/central/issues/98
```

---

## Phase 2 Complete: Testing Checkpoint

Before proceeding to Phase 3, verify rebase success:

### Quick Smoke Tests

**1. Syntax Check**
```bash
# Check for syntax errors in modified files
node -c lib/model/query/sessions.js
node -c lib/resources/sessions.js
node -c lib/model/query/users.js
node -c lib/util/vg-password.js
```

**2. Dependency Check**
```bash
# Ensure package.json unchanged (or conflicts resolved)
git diff HEAD~1 package.json

# If changed, run
npm install
```

**3. Build Check (if applicable)**
```bash
# Check if server starts (don't run migrations yet)
# Just check for syntax/import errors
node lib/bin/run-server.js --help
```

### Rollback Decision Point

**Proceed to Phase 3 if:**
- ✅ Rebase completed successfully
- ✅ No syntax errors in modified files
- ✅ Git history looks clean
- ✅ All VG files present

**Rollback if:**
- ❌ Rebase failed with unresolvable conflicts
- ❌ Syntax errors in critical files
- ❌ VG files missing or corrupted
- ❌ Git history corrupted

**Rollback Command:**
```bash
cd server
git reset --hard vg-work-pre-rebase-2025.4.0
cd ..
git add server
git commit -m "Rollback: Restore server to pre-rebase state (Phase 2 failed)"
git push --force-with-lease
```

---

## Testing Checklist After Rebase

Before Phase 3, perform these quick checks:

### File Presence Check
```bash
# VG domain files
ls -1 server/lib/domain/vg-*.js
# Should list: vg-app-user-auth.js, vg-enketo-status.js, vg-telemetry.js

# VG query files
ls -1 server/lib/model/query/vg-*.js
# Should list: vg-app-user-auth.js, vg-enketo-status.js, vg-telemetry.js

# VG resource files
ls -1 server/lib/resources/vg-*.js
# Should list: vg-app-user-auth.js, vg-enketo-status.js, vg-telemetry.js

# VG tests
ls -1 server/test/integration/api/vg-*.js
# Should list: vg-app-user-auth.js, vg-enketo-status*.js, vg-telemetry.js, etc.

# VG SQL
ls -1 server/docs/sql/vg_*.sql
# Should list: vg_app_user_auth.sql
```

### Git History Check
```bash
# Verify VG commits preserved
git log --oneline --all --grep="VG:" | wc -l
# Should show ~20+ VG commits

# Verify no squashed commits
git log --oneline -20
# Should show individual VG commit messages, not "Rebase: squashed commits"

# Check merge base
git log --oneline --graph --decorate -10
# Should show linear history on top of upstream/master
```

### Critical File Integrity Check
```bash
# Session management (high-risk files)
grep -n "trimByActorId" server/lib/model/query/sessions.js
# Should find function definition and export

grep -n "vg_field_key_auth" server/lib/model/query/sessions.js
# Should find in getByBearerToken query

grep -n "recordFailureAndMaybeLockout" server/lib/resources/sessions.js
# Should find VG login hardening logic

# Password validation
grep -n "validateVgPassword" server/lib/util/vg-password.js
# Should find function definition

grep -n "length > 72" server/lib/util/vg-password.js
# Should find 72-byte check (if enhancement applied)

# Users query
grep -n "getAnyPasswordHash" server/lib/model/query/users.js
# Should find function definition and export
```

---

## Next Steps

**If Phase 2 Successful:**
→ Proceed to **Phase 3: Testing** (central-xav.13)

**Phase 3 Tasks:**
- P3.1: Apply VG database schema and run migrations
- P3.2: Run VG unit tests
- P3.3: Run VG integration tests
- P3.4: Manual testing of VG features
- P3.5: Run full upstream test suite

**If Phase 2 Failed:**
→ Execute **Rollback Plan**
→ Review conflict resolution strategy
→ Consider alternative approach or request assistance

---

## Reference Documents

All detailed analysis available in:
- `analysis-session-management-conflicts.md` - Session management deep dive
- `analysis-auth-password-conflicts.md` - Password validation analysis
- `analysis-database-migration-conflicts.md` - Database schema analysis
- `pre-rebase-state-v2024.3.1.md` - VG fork state before rebase
- `rebase-v2025.4.0-plan.md` - Overall rebase plan with all phases

---

## Emergency Contacts

If stuck during Phase 2:
1. Check analysis documents for context
2. Review git rebase documentation: `git rebase --help`
3. Check rebase status: `git status`
4. View conflict: `git diff <file>`
5. Abort if needed: `git rebase --abort`

---

**Playbook Status:** ✅ Ready for Phase 2 Execution
**Next Action:** Execute P2.1 (Start interactive rebase)
**Estimated Duration:** 2-4 hours
**Confidence Level:** HIGH (all conflicts analyzed and planned)

---

**Last Updated:** 2026-01-12
**Author:** VG + Claude Sonnet 4.5
**Version:** 1.0
