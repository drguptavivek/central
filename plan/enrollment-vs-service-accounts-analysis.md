# Plan Conflict Analysis: TOTP Enrollment vs Service Account Security

> **Generated:** 2026-02-09
> **Analyzes:** Interactions between `2Fa-Enrollment-Flow.md` and `service-account-security-v2.md`

---

## Executive Summary

**CRITICAL FINDING:** The two plans have **significant interactions** that require coordination:

1. ⚠️ **Service accounts must be EXCLUDED from TOTP enrollment** (they're automated systems, not humans)
2. ⚠️ **Both plans modify the same file** (`sessions.js`) - changes must be coordinated
3. ⚠️ **API token creation** interacts with mandatory enrollment (can't create tokens until TOTP is set up)

**RECOMMENDATION:** Update both plans to handle service accounts correctly.

---

## Plan A: TOTP Enrollment (In Progress)

**Goal:** Prompt users to enable 2FA (mandatory for admins, optional for others)

**Key Features:**
- Mandatory 2FA for configured roles (e.g., admin)
- Optional prompts for other users (dismissible)
- System setting: `vg_totp_mandatory_roles` (JSON array of role IDs)
- Database: Add columns to `vg_web_user_totp` table

**Status:** 13 open issues, 10 ready to work

---

## Plan B: Service Account Security (New)

**Goal:** Secure automated systems with API tokens + mandatory IP whitelist

**Key Features:**
- API tokens (long-lived, TOTP-protected creation)
- Service account flag (`users.is_service_account`)
- Mandatory IP whitelist for service accounts
- 1-hour sessions for service accounts (vs 24 hours)

**Status:** Not yet tracked (~20 new issues needed)

---

## Interaction Matrix

| Feature | Regular Users | Service Accounts | Conflict? |
|---------|--------------|------------------|-----------|
| **TOTP Enrollment Prompts** | ✅ YES (Plan A) | ❌ NO (must exclude) | ⚠️ YES |
| **Mandatory TOTP (by role)** | ✅ YES (if admin) | ❌ NO (automated) | ⚠️ YES |
| **API Tokens** | ✅ YES (Plan B) | ✅ YES (Plan B) | ✅ No conflict |
| **IP Whitelist** | 🔵 Optional | 🔴 MANDATORY (Plan B) | ✅ No conflict |
| **Session Lifetime** | 24 hours | 1 hour (Plan B) | ✅ No conflict |
| **TOTP for Auth** | ✅ Required if enabled | ❌ Not applicable | ⚠️ YES |

**Legend:**
- ✅ No conflict - Plans compatible
- ⚠️ YES - Requires coordination

---

## Critical Conflicts

### Conflict 1: Service Accounts and TOTP Enrollment

**Problem:**
- Enrollment plan: "Prompt ALL users without TOTP" (including service accounts)
- Service account plan: "Service accounts are automated systems" (no human to set up TOTP)
- **If admin marks user as service account, enrollment prompts will still trigger!**

**Example Scenario:**
```
1. Admin creates user "ci-pipeline@example.com" for CI/CD automation
2. Admin marks it as service account (is_service_account = true)
3. User logs in with username/password (to create API token)
4. ❌ PROBLEM: Enrollment prompt appears! But this is a bot, not a human.
5. If admin role is mandatory for 2FA → BLOCKS service account from working!
```

**Impact:** HIGH - Service accounts cannot function if forced to set up TOTP

**Resolution Required:** Update enrollment logic to skip service accounts

---

### Conflict 2: Both Plans Modify `sessions.js`

**Enrollment Plan Changes:**
```javascript
// Around line 150 in sessions.js
return VgWebUserTotp.isRoleMandatoryForTotp(user.actorId)
  .then((isMandatory) => {
    if (isMandatory) {
      // Return requireTotpSetup: true
    }
    // Check shouldPromptEnrollment
  });
```

**Service Account Plan Changes:**
```javascript
// In sessions.js - session creation
if (user.isServiceAccount) {
  // 1-hour session instead of 24-hour
}

// In preprocessors.js
if (user.isServiceAccount && !ipWhitelisted) {
  // Reject request
}
```

**Impact:** MEDIUM - Both plans touch session creation logic

**Resolution Required:** Coordinate changes, ensure proper order of checks

---

### Conflict 3: API Token Creation and Mandatory TOTP

**Service Account Plan:**
```
POST /v1/users/:id/api-tokens
→ Requires TOTP verification IF user has 2FA enabled
```

**Enrollment Plan:**
```
Admin users MUST have TOTP enabled before accessing system
```

**Problem Scenario:**
```
1. Admin creates new admin user "alice@example.com"
2. Alice logs in → Forced to set up TOTP (mandatory enrollment)
3. Alice needs to create API token for automation
4. ✅ This works! TOTP is already enabled
```

**But what if:**
```
1. Service account "bot@example.com" (is_service_account = true)
2. Bot needs API token
3. Bot doesn't have TOTP enabled (automated system)
4. ❌ Token creation blocked? Should service accounts need TOTP for token creation?
```

**Impact:** MEDIUM - Need to define TOTP requirements for service account API tokens

**Resolution Required:** Clarify TOTP requirements for service accounts

---

## Required Updates

### Update 1: Enrollment Plan - Exclude Service Accounts

**File:** `server/lib/model/query/vg-web-user-totp.js`

**Method:** `shouldPromptEnrollment()`

**Change:**
```javascript
// BEFORE (current plan)
const shouldPromptEnrollment = (actorId) => ({ maybeOne }) =>
  maybeOne(sql`
    SELECT totp_enabled, totp_prompt_dismissed_at, totp_prompt_remind_after
    FROM vg_web_user_totp
    WHERE "actorId" = ${actorId}
  `).then((maybeRecord) => {
    // ... enrollment logic
  });

// AFTER (updated to exclude service accounts)
const shouldPromptEnrollment = (actorId) => ({ maybeOne }) =>
  // FIRST: Check if user is a service account
  maybeOne(sql`
    SELECT u.is_service_account
    FROM users u
    WHERE u."actorId" = ${actorId}
  `).then((maybeUser) => {
    // Service accounts NEVER get enrollment prompts
    if (maybeUser.isDefined() && maybeUser.get().is_service_account) {
      return false;
    }

    // Regular users: check enrollment status
    return maybeOne(sql`
      SELECT totp_enabled, totp_prompt_dismissed_at, totp_prompt_remind_after
      FROM vg_web_user_totp
      WHERE "actorId" = ${actorId}
    `).then((maybeRecord) => {
      // ... rest of enrollment logic
    });
  });
```

**Method:** `isRoleMandatoryForTotp()`

**Change:**
```javascript
// BEFORE
const isRoleMandatoryForTotp = (actorId) => ({ maybeOne }) =>
  Promise.all([
    maybeOne(sql`SELECT u.role FROM users u WHERE u."actorId" = ${actorId}`),
    VgSettings.get('vg_totp_mandatory_roles')
  ]).then(([maybeUser, mandatoryRolesSetting]) => {
    // ... check if role is mandatory
  });

// AFTER (exclude service accounts)
const isRoleMandatoryForTotp = (actorId) => ({ maybeOne }) =>
  maybeOne(sql`
    SELECT u.role, u.is_service_account
    FROM users u
    WHERE u."actorId" = ${actorId}
  `).then((maybeUser) => {
    if (!maybeUser.isDefined()) return false;

    const user = maybeUser.get();

    // Service accounts NEVER have mandatory TOTP (they use IP whitelist)
    if (user.is_service_account) {
      return false;
    }

    // Regular users: check role against mandatory list
    return VgSettings.get('vg_totp_mandatory_roles')
      .then((mandatoryRolesSetting) => {
        const mandatoryRoles = JSON.parse(mandatoryRolesSetting || '["admin"]');
        return mandatoryRoles.includes(user.role);
      });
  });
```

---

### Update 2: Service Account Plan - Clarify TOTP Requirements

**File:** `service-account-security-v2.md`

**Section:** Part 1: API Token Management → TOTP Protection

**Add:**
```markdown
## TOTP Protection for API Token Creation

### Regular Users
- Token creation requires TOTP verification IF user has 2FA enabled
- If user is in mandatory role but hasn't set up TOTP yet:
  - User must complete mandatory enrollment FIRST
  - Then can create API tokens

### Service Accounts (is_service_account = true)
- Token creation does NOT require TOTP verification
- Service accounts rely on IP whitelist, not TOTP
- Rationale: Automated systems cannot perform 2FA verification
```

**File:** `server/lib/resources/vg-api-tokens.js`

**Endpoint:** `POST /v1/users/:id/api-tokens`

**Add Check:**
```javascript
service.post('/v1/users/:id/api-tokens', endpoint(async (container, { auth, params, body }) => {
  const { VgApiTokens, Users, VgWebUserTotp } = container;
  const user = await Users.getByActorId(params.id).then(getOrNotFound);

  // Authorization check
  await auth.canOrReject('user.update', user);

  // TOTP verification (ONLY for regular users, NOT service accounts)
  if (!user.isServiceAccount) {
    const hasTotpEnabled = await VgWebUserTotp.isEnabled(user.actorId);
    if (hasTotpEnabled) {
      // Verify TOTP token from request body
      const { totpToken } = body;
      if (!totpToken) {
        throw Problem.user.missingParameter({ expected: 'totpToken' });
      }
      await VgWebUserTotp.verify(user.actorId, totpToken);
    }
  }

  // Generate and store token
  // ...
}));
```

---

### Update 3: Coordinate `sessions.js` Changes

**File:** `server/lib/resources/sessions.js`

**Combined Logic:**
```javascript
// POST /v1/sessions response (around line 150)

// Check TOTP status
if (user has TOTP enabled) {
  // Existing: Return requireTotp: true for verification
  return { requireTotp: true, ... };
}

// NEW: Check if user is service account
if (user.isServiceAccount) {
  // Service accounts:
  // - 1-hour sessions (not 24 hours)
  // - NO enrollment prompts
  // - IP whitelist enforced in preprocessors
  const sessionExpiry = new Date(Date.now() + 1 * 60 * 60 * 1000);  // 1 hour
  return createUserSession(user, sessionExpiry, false);  // No enrollment flag
}

// NEW: Check mandatory TOTP enrollment (regular users only)
const isMandatory = await VgWebUserTotp.isRoleMandatoryForTotp(user.actorId);
if (isMandatory) {
  // Force TOTP setup for mandatory roles
  return { requireTotpSetup: true, mandatory: true, ... };
}

// NEW: Check optional enrollment prompt (regular users only)
const shouldPrompt = await VgWebUserTotp.shouldPromptEnrollment(user.actorId);
return createUserSession(user, 24hours, true)
  .then((session) => ({
    ...session,
    shouldPromptTotpEnrollment: shouldPrompt
  }));
```

**Order of Checks:**
1. ✅ TOTP enabled? → Require TOTP verification (existing)
2. ✅ Service account? → 1hr session, no prompts (NEW)
3. ✅ Mandatory role? → Force setup (NEW - enrollment)
4. ✅ Should prompt? → Optional prompt (NEW - enrollment)

---

### Update 4: Service Account Creation Workflow

**File:** `server/lib/resources/vg-service-users.js`

**Endpoint:** `PATCH /v1/users/:id/service-account`

**Add:**
```javascript
service.patch('/v1/users/:id/service-account', endpoint(async (container, { auth, params, body }) => {
  // ... existing validation (IP whitelist required)

  // Mark as service account
  await Users.update(userId, { is_service_account: true });

  // ALSO: Permanently dismiss enrollment prompts for this account
  await VgWebUserTotp.dismissEnrollmentPrompt(actorId, null);  // Permanent dismissal

  // Audit log
  await Audits.log(auth.actor, 'user.service_account.mark', user, {
    message: 'Marked as service account - TOTP enrollment disabled'
  });

  return { success: true };
}));
```

---

## Updated Authentication Matrix

| User Type | TOTP Enrollment | TOTP for Auth | IP Whitelist | Session Lifetime | API Tokens |
|-----------|----------------|---------------|--------------|------------------|------------|
| **Regular User** | Optional (dismissible) | If enabled | Optional | 24 hours | ✅ YES (TOTP if enabled) |
| **Admin (mandatory role)** | MANDATORY | Required | Optional | 24 hours | ✅ YES (requires TOTP) |
| **Service Account** | ❌ NONE (excluded) | ❌ NO | MANDATORY | 1 hour | ✅ YES (no TOTP) |

---

## Implementation Order (REVISED)

### Option A: Sequential (Recommended)

```
Phase 1: Complete TOTP Enrollment (with service account exclusions)
├── Update enrollment logic to check is_service_account
├── Test: Service accounts don't get prompts
└── Close enrollment epic (central-2y6)

Phase 2: Implement Service Account Flag
├── Migration: Add is_service_account column
├── Endpoint: PATCH /v1/users/:id/service-account
├── Update sessions.js for 1hr lifetime
├── Update preprocessors.js for mandatory IP check
└── Test: Service account authentication

Phase 3: Implement API Token Management
├── Migration: vg_api_tokens table
├── Endpoints: POST/GET/DELETE /v1/users/:id/api-tokens
├── Add TOTP check (exclude service accounts)
├── Frontend UI
└── Test: Token creation and authentication
```

**Why this order:**
1. Enrollment work is 77% ready (10 of 13 tasks unblocked)
2. Adding service account exclusions is a small change
3. Service account flag provides foundation for API tokens
4. API tokens build on both previous features

---

### Option B: Parallel (If Multiple Developers)

```
Developer 1:
- Complete enrollment work (with service account exclusions)

Developer 2:
- Implement service account flag
- Coordinate sessions.js changes with Dev 1

Developer 3:
- Design API token system
- Wait for service account flag before implementing

Sync Point: Integration testing after all three complete
```

---

## Updated Beads Issues Needed

### Enrollment Epic Updates (central-2y6)

**New Subtasks to Add:**
- [ ] `central-xxx`: Update shouldPromptEnrollment() to exclude service accounts
- [ ] `central-xxx`: Update isRoleMandatoryForTotp() to exclude service accounts
- [ ] `central-xxx`: Test: Service account doesn't get enrollment prompts
- [ ] `central-xxx`: Test: Service account marked during mandatory role

**Estimated:** 4 additional tasks

---

### Service Account Epic (NEW)

**Create Epic:** `EPIC: Service Account Security System`

**Subtasks:**
- [ ] Migration: Add is_service_account column to users table
- [ ] Update User frame: Add isServiceAccount getter
- [ ] Endpoint: PATCH /v1/users/:id/service-account (with IP whitelist validation)
- [ ] Update sessions.js: 1hr lifetime for service accounts
- [ ] Update preprocessors.js: Mandatory IP whitelist enforcement
- [ ] Coordinate sessions.js changes with enrollment plan
- [ ] Test: Service account creation (requires IP whitelist)
- [ ] Test: Service account session lifetime (1hr not 24hr)
- [ ] Test: Service account IP whitelist enforcement
- [ ] Test: Service account excluded from enrollment
- [ ] Frontend UI: Service account toggle component
- [ ] Documentation: Route docs + core edits

**Estimated:** 12 tasks

---

### API Token Epic (NEW)

**Create Epic:** `EPIC: API Token Management System`

**Subtasks:**
- [ ] Design API contract
- [ ] Migration: Create vg_api_tokens table
- [ ] Implement VgApiTokens query module
- [ ] Endpoint: POST /v1/users/:id/api-tokens (with TOTP check, exclude service accounts)
- [ ] Endpoint: GET /v1/users/:id/api-tokens
- [ ] Endpoint: DELETE /v1/users/:id/api-tokens/:tokenId
- [ ] Update preprocessors.js: Detect and authenticate API tokens
- [ ] Test: API token creation (regular users with TOTP)
- [ ] Test: API token creation (service accounts without TOTP)
- [ ] Test: API token authentication
- [ ] Test: API token revocation
- [ ] Frontend UI: Token management component
- [ ] Documentation: Route docs + admin guide

**Estimated:** 13 tasks

---

## Total Revised Effort

| Work Stream | Issues | Status |
|-------------|--------|--------|
| **Enrollment (existing)** | 13 + 4 = 17 | 10 ready, 7 blocked/new |
| **Service Account (new)** | 12 | Not created |
| **API Tokens (new)** | 13 | Not created |
| **TOTAL** | **42 tasks** | ~24% ready (10 of 42) |

---

## Recommendation

**Adopt Option A: Sequential Implementation**

### Rationale:
1. ✅ Enrollment work is mostly ready (10 tasks unblocked)
2. ✅ Adding service account exclusions is low-risk (4 tasks)
3. ✅ Provides clean foundation for service account flag
4. ✅ Minimizes coordination overhead (no parallel merge conflicts)
5. ✅ Clear progress milestones

### Next Steps:
1. **Update enrollment issues** (4 new tasks for service account exclusions)
2. **Complete enrollment epic** (central-2y6 + new tasks)
3. **Create service account issues** (12 tasks)
4. **Create API token issues** (13 tasks)
5. **Implement sequentially** (TDD approach throughout)

---

## Critical Success Factors

### Must-Haves:
- ✅ Service accounts NEVER get TOTP enrollment prompts
- ✅ Service accounts can create API tokens WITHOUT TOTP verification
- ✅ Regular users in mandatory roles MUST set up TOTP before creating tokens
- ✅ Coordinated changes to sessions.js don't conflict
- ✅ All scenarios covered in integration tests

### Documentation:
- ✅ Update enrollment docs to explain service account exclusions
- ✅ Update service account docs to explain TOTP exemption
- ✅ Update authentication flow diagrams with combined logic
- ✅ Document all core file edits (sessions.js, preprocessors.js)

---

## Conclusion

**Status:** Plans are COMPATIBLE but require COORDINATION

**Action Required:**
1. Update enrollment plan to exclude service accounts (4 new tasks)
2. Update service account plan to clarify TOTP requirements
3. Coordinate sessions.js changes between both plans
4. Choose implementation order (recommend Sequential/Option A)

**Risk Level:** MEDIUM (manageable with proper coordination)

**Confidence:** HIGH (clear path forward identified)
