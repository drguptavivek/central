# Task: TOTP 2FA Enrollment - Role-Based Mandatory Enforcement

## Context

Users currently can enable TOTP 2FA voluntarily through their account settings. However, many users may not be aware of this security feature or forget to enable it. This task implements a flexible two-tier enrollment system:

1. **Mandatory 2FA for Configured Roles**: System administrators can specify which roles MUST have 2FA enabled via a system setting (`vg_totp_mandatory_roles`). Users in these roles are forced to set up 2FA during login if they haven't already - they cannot access the system until TOTP is configured.

2. **Gentle Prompt for Other Users**: Users not in mandatory roles receive a dismissible prompt encouraging 2FA enrollment, but are not forced to enable it.

This configurable approach allows organizations to enforce 2FA for sensitive roles (e.g., admins, data managers) while maintaining usability for other users.

---

## Current Flow (No Enrollment Prompt)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER LOGS IN                                                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ POST /v1/sessions                     │
        │ { email, password }                   │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Backend: Check TOTP status            │
        └───────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    ┌─────────────────┐         ┌─────────────────┐
    │ TOTP ENABLED    │         │ TOTP NOT ENABLED│
    └─────────────────┘         └─────────────────┘
              │                           │
              ▼                           ▼
    ┌─────────────────┐         ┌─────────────────┐
    │ Return:         │         │ Return:         │
    │ requireTotp:    │         │ Session data    │
    │ true            │         │ (cookies set)   │
    │ (no cookies)    │         │                 │
    └─────────────────┘         └─────────────────┘
              │                           │
              ▼                           │
    ┌─────────────────┐                  │
    │ Show TOTP input │                  │
    │ Enter 6-digit   │                  │
    │ code            │                  │
    └─────────────────┘                  │
              │                           │
              ▼                           │
    ┌─────────────────┐                  │
    │ POST /sessions/ │                  │
    │ totp-verify     │                  │
    └─────────────────┘                  │
              │                           │
              ▼                           │
    ┌─────────────────┐                  │
    │ Cookies set     │                  │
    │ Session active  │                  │
    └─────────────────┘                  │
              │                           │
              └─────────────┬─────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │ logIn()                 │
              │ Fetch current user      │
              └─────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │ Navigate to Dashboard   │
              │ (No enrollment prompt)  │ ◄── NO PROMPT SHOWN
              └─────────────────────────┘
```

**Issues with current flow:**
- Users who don't have 2FA are never prompted to enable it
- Security feature remains hidden in settings
- Low adoption rate for voluntary 2FA enrollment

---

## Proposed Flow (With Enrollment Prompt)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER LOGS IN                                                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ POST /v1/sessions                     │
        │ { email, password }                   │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Backend: Check TOTP status            │
        └───────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    ┌─────────────────┐         ┌─────────────────────────────┐
    │ TOTP ENABLED    │         │ TOTP NOT ENABLED            │
    └─────────────────┘         └─────────────────────────────┘
              │                           │
              │                           ▼
              │                 ┌─────────────────────────────┐
              │                 │ NEW: Check enrollment       │
              │                 │ prompt status               │
              │                 │ shouldPromptEnrollment()    │
              │                 └─────────────────────────────┘
              │                           │
              │              ┌────────────┴────────────┐
              │              │                         │
              │              ▼                         ▼
              │     ┌────────────────┐      ┌────────────────┐
              │     │ Should prompt  │      │ Don't prompt   │
              │     │ (never prompted│      │ (dismissed or  │
              │     │  or remind     │      │  recently      │
              │     │  date passed)  │      │  prompted)     │
              │     └────────────────┘      └────────────────┘
              │              │                         │
              ▼              ▼                         │
    ┌─────────────────┐  ┌─────────────────┐         │
    │ Return:         │  │ Return:         │         │
    │ requireTotp:    │  │ Session data    │         │
    │ true            │  │ promptEnroll:   │         │
    │ (no cookies)    │  │ true ◄─ NEW     │         │
    └─────────────────┘  └─────────────────┘         │
              │              │                         │
              ▼              │                         │
    [TOTP verify flow]       │                         │
    (same as before)         │                         │
              │              │                         │
              └────────┬─────┴─────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │ logIn()                 │
         │ Fetch current user      │
         │ Store promptEnroll flag │
         └─────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
┌──────────────────┐      ┌──────────────────┐
│ promptEnroll     │      │ promptEnroll     │
│ = true           │      │ = false          │
└──────────────────┘      └──────────────────┘
         │                           │
         ▼                           │
┌──────────────────┐                 │
│ Navigate to      │                 │
│ Dashboard        │                 │
└──────────────────┘                 │
         │                           │
         ▼                           │
┌──────────────────────────┐         │
│ Dashboard mounted        │         │
│ Check pendingPrompt flag │         │
└──────────────────────────┘         │
         │                           │
         ▼                           │
┌──────────────────────────┐         │
│ Show Modal:              │         │
│ ┌──────────────────────┐ │         │
│ │ 🔒 Secure Your      │ │         │
│ │    Account with 2FA │ │         │
│ │                     │ │         │
│ │ [Set Up Now]        │ │         │
│ │ [Remind Me Later]   │ │         │
│ │ [Don't Ask Again]   │ │         │
│ └──────────────────────┘ │         │
└──────────────────────────┘         │
         │                           │
    ┌────┴────┐                      │
    │         │                      │
    ▼         ▼                      ▼
┌────────┐ ┌────────┐    ┌────────────────┐
│Set Up  │ │Remind  │    │ No prompt      │
│Now     │ │Later   │    │ shown          │
└────────┘ └────────┘    └────────────────┘
    │         │                      │
    ▼         ▼                      │
┌────────┐ ┌────────────────────┐   │
│Open    │ │POST /users/:id/    │   │
│TOTP    │ │totp/dismiss-prompt │   │
│setup   │ │{remindAfterDays:7} │   │
│modal   │ └────────────────────┘   │
└────────┘         │                 │
    │              ▼                 │
    │    ┌─────────────────────┐    │
    │    │ Update DB:          │    │
    │    │ remind_after =      │    │
    │    │ now() + 7 days      │    │
    │    └─────────────────────┘    │
    │              │                 │
    └──────────────┴─────────────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Continue using  │
          │ application     │
          └─────────────────┘
```

**Benefits of proposed flow:**
- ✅ Non-intrusive: Shows after successful login, not blocking it
- ✅ User control: "Remind me later" option (7 days default)
- ✅ Persistent dismissal: "Don't ask again" honors user choice
- ✅ Security improvement: Increases 2FA adoption rate
- ✅ Gentle nudge: Educates users about available security feature

---

## Mandatory Enrollment Flow (For Configured Roles)

```
┌─────────────────────────────────────────────────────────────────┐
│ USER IN MANDATORY ROLE LOGS IN (e.g., Admin)                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ POST /v1/sessions                     │
        │ { email, password }                   │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Backend: Verify password              │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Check TOTP status                     │
        └───────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    ┌─────────────────┐         ┌─────────────────────┐
    │ TOTP ENABLED    │         │ TOTP NOT ENABLED    │
    └─────────────────┘         └─────────────────────┘
              │                           │
              ▼                           ▼
    ┌─────────────────┐         ┌─────────────────────┐
    │ Return:         │         │ Check user role      │
    │ requireTotp:    │         │ against mandatory    │
    │ true            │         │ roles setting        │
    │ (normal 2FA     │         └─────────────────────┘
    │  flow)          │                   │
    └─────────────────┘         ┌─────────┴─────────┐
              │                 │                   │
              │                 ▼                   ▼
              │      ┌──────────────────┐  ┌──────────────┐
              │      │ Role IS in       │  │ Role NOT in  │
              │      │ mandatory list   │  │ mandatory    │
              │      └──────────────────┘  │ list         │
              │                 │          └──────────────┘
              │                 ▼                   │
              │      ┌──────────────────┐          │
              │      │ Return:          │          │
              │      │ requireTotpSetup:│          │
              │      │ true (MANDATORY) │          │
              │      │ (no cookies)     │          │
              │      └──────────────────┘          │
              │                 │                  │
              │                 ▼                  ▼
              │      ┌──────────────────┐  [Optional prompt
              │      │ Frontend:        │   flow as shown
              │      │ Show FORCED      │   above]
              │      │ setup modal      │
              │      │ (no dismiss)     │
              │      └──────────────────┘
              │                 │
              │                 ▼
              │      ┌──────────────────┐
              │      │ POST /users/:id/ │
              │      │ totp/setup       │
              │      │ → Get QR code    │
              │      └──────────────────┘
              │                 │
              │                 ▼
              │      ┌──────────────────┐
              │      │ User scans QR    │
              │      │ in auth app      │
              │      └──────────────────┘
              │                 │
              │                 ▼
              │      ┌──────────────────┐
              │      │ Enter 6-digit    │
              │      │ code             │
              │      └──────────────────┘
              │                 │
              │                 ▼
              │      ┌──────────────────┐
              │      │ POST /users/:id/ │
              │      │ totp/enable      │
              │      │ {token: "123456"}│
              │      └──────────────────┘
              │                 │
              │                 ▼
              │      ┌──────────────────┐
              │      │ TOTP enabled!    │
              │      │ Close modal      │
              │      └──────────────────┘
              │                 │
              │                 ▼
              │      ┌──────────────────┐
              │      │ POST /v1/sessions│
              │      │ (re-login)       │
              │      └──────────────────┘
              │                 │
              │                 ▼
              │      ┌──────────────────┐
              │      │ Now returns:     │
              │      │ requireTotp:true │
              │      │ (normal 2FA flow)│
              │      └──────────────────┘
              │                 │
              └─────────────────┴─────────────────────┐
                                                      │
                                                      ▼
                                          ┌──────────────────┐
                                          │ Enter TOTP code  │
                                          │ POST /sessions/  │
                                          │ totp-verify      │
                                          └──────────────────┘
                                                      │
                                                      ▼
                                          ┌──────────────────┐
                                          │ Cookies set      │
                                          │ Session active   │
                                          │ Navigate to      │
                                          │ Dashboard        │
                                          └──────────────────┘
```

**Key differences for mandatory enrollment:**
- ❌ No "Remind me later" or "Don't ask again" buttons
- ❌ Cannot close modal or navigate away
- ✅ Must complete TOTP setup to access system
- ✅ Clear messaging: "Your role requires 2FA"
- ✅ After setup, normal 2FA login flow applies

---

## System Setting

### New Setting: `vg_totp_mandatory_roles`

**Type:** JSON array of role IDs

**Default value:** `["admin"]` (only admins require 2FA by default)

**Example values:**
```json
["admin"]                           // Only admins
["admin", "manager"]                // Admins and managers
["admin", "manager", "data-clerk"]  // Multiple roles
[]                                  // No mandatory enforcement
```

**Storage:** `vg_settings` table

```sql
INSERT INTO vg_settings (key, value, created_at, updated_at)
VALUES (
  'vg_totp_mandatory_roles',
  '["admin"]',
  now(),
  now()
);
```

**Admin UI:** New section in System Settings page to configure mandatory roles with checkboxes for each available role.

---

## Database Schema Changes

### Option 1: Add to existing table (simpler)

```sql
ALTER TABLE vg_web_user_totp ADD COLUMN IF NOT EXISTS
  totp_prompt_dismissed_at timestamptz NULL;

ALTER TABLE vg_web_user_totp ADD COLUMN IF NOT EXISTS
  totp_prompt_remind_after timestamptz NULL;

-- Index for quick lookup
CREATE INDEX idx_vg_web_user_totp_prompt_remind
  ON vg_web_user_totp(totp_prompt_remind_after)
  WHERE totp_prompt_remind_after IS NOT NULL;
```

### Option 2: Separate tracking table (more flexible)

```sql
CREATE TABLE vg_web_user_totp_enrollment_prompts (
  "actorId" integer PRIMARY KEY REFERENCES users("actorId") ON DELETE CASCADE,
  dismissed_permanently_at timestamptz NULL,
  remind_after timestamptz NULL,
  prompt_count integer DEFAULT 0,
  last_prompted_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_vg_totp_prompts_remind
  ON vg_web_user_totp_enrollment_prompts(remind_after)
  WHERE remind_after IS NOT NULL;
```

**Recommendation: Option 1** - Simpler, fewer joins, sufficient for this use case.

---

## Implementation Plan

### 1. Backend Changes

#### 1.1 Database Migration

**File:** `server/lib/model/migrations/20260208-01-totp-enrollment-prompts.sql`

```sql
-- Add prompt tracking columns to existing TOTP table
ALTER TABLE vg_web_user_totp ADD COLUMN IF NOT EXISTS
  totp_prompt_dismissed_at timestamptz NULL;

ALTER TABLE vg_web_user_totp ADD COLUMN IF NOT EXISTS
  totp_prompt_remind_after timestamptz NULL;

-- Index for efficient prompt status queries
CREATE INDEX IF NOT EXISTS idx_vg_web_user_totp_prompt_remind
  ON vg_web_user_totp(totp_prompt_remind_after)
  WHERE totp_prompt_remind_after IS NOT NULL AND totp_enabled = false;

-- Add system setting for mandatory 2FA roles
INSERT INTO vg_settings (key, value, created_at, updated_at)
VALUES (
  'vg_totp_mandatory_roles',
  '["admin"]',  -- Default: only admins require 2FA
  now(),
  now()
)
ON CONFLICT (key) DO NOTHING;
```

#### 1.2 Query Module

**File:** `server/lib/model/query/vg-web-user-totp.js`

Add methods:

```javascript
const { getOrElse } = require('../util/promise');
const { VgSettings } = require('./vg-settings');

// Check if user role requires mandatory TOTP enrollment
const isRoleMandatoryForTotp = (actorId) => ({ maybeOne }) =>
  Promise.all([
    // Get user's role
    maybeOne(sql`
      SELECT u.role
      FROM users u
      WHERE u."actorId" = ${actorId}
    `),
    // Get mandatory roles setting
    VgSettings.get('vg_totp_mandatory_roles')
  ]).then(([maybeUser, mandatoryRolesSetting]) => {
    if (!maybeUser.isDefined()) return false;

    const userRole = maybeUser.get().role;
    const mandatoryRoles = JSON.parse(mandatoryRolesSetting || '["admin"]');

    return mandatoryRoles.includes(userRole);
  });

// Check if user should be prompted for TOTP enrollment (non-mandatory users only)
const shouldPromptEnrollment = (actorId) => ({ maybeOne }) =>
  maybeOne(sql`
    SELECT
      totp_enabled,
      totp_prompt_dismissed_at,
      totp_prompt_remind_after
    FROM vg_web_user_totp
    WHERE "actorId" = ${actorId}
  `).then((maybeRecord) => {
    if (!maybeRecord.isDefined()) {
      // No record = never enabled, never prompted → SHOULD PROMPT
      return true;
    }

    const record = maybeRecord.get();

    // Already has TOTP enabled → DON'T PROMPT
    if (record.totp_enabled) return false;

    // Dismissed permanently → DON'T PROMPT
    if (record.totp_prompt_dismissed_at != null) return false;

    // Remind later date set and not yet passed → DON'T PROMPT
    if (record.totp_prompt_remind_after != null &&
        new Date(record.totp_prompt_remind_after) > new Date()) {
      return false;
    }

    // Otherwise → SHOULD PROMPT
    return true;
  });

// Dismiss enrollment prompt (permanently or with reminder)
// NOTE: Only works for non-mandatory users; mandatory users cannot dismiss
const dismissEnrollmentPrompt = (actorId, remindAfterDays = null) => ({ run }) => {
  if (remindAfterDays === null) {
    // Permanent dismissal
    return run(sql`
      INSERT INTO vg_web_user_totp ("actorId", totp_prompt_dismissed_at, created_at, updated_at)
      VALUES (${actorId}, now(), now(), now())
      ON CONFLICT ("actorId")
      DO UPDATE SET
        totp_prompt_dismissed_at = now(),
        totp_prompt_remind_after = NULL,
        updated_at = now()
    `);
  } else {
    // Remind later
    const remindAfter = new Date();
    remindAfter.setDate(remindAfter.getDate() + remindAfterDays);

    return run(sql`
      INSERT INTO vg_web_user_totp ("actorId", totp_prompt_remind_after, created_at, updated_at)
      VALUES (${actorId}, ${remindAfter.toISOString()}, now(), now())
      ON CONFLICT ("actorId")
      DO UPDATE SET
        totp_prompt_remind_after = ${remindAfter.toISOString()},
        updated_at = now()
    `);
  }
};

module.exports = {
  // ... existing exports
  isRoleMandatoryForTotp,
  shouldPromptEnrollment,
  dismissEnrollmentPrompt
};
```

#### 1.3 Sessions Resource

**File:** `server/lib/resources/sessions.js`

Modify POST /v1/sessions response (around line 150):

```javascript
// No TOTP, create normal session (fully verified)
// But first check if user's role requires mandatory TOTP enrollment
return VgWebUserTotp.isRoleMandatoryForTotp(user.actorId)
  .then((isMandatory) => {
    if (isMandatory) {
      // Mandatory role without TOTP → BLOCK login, force setup
      // Return special response WITHOUT setting cookies
      const tempSessionExpiry = new Date(Date.now() + 5 * 60 * 1000);  // 5 minutes
      return Promise.all([
        Sessions.create(user.actor, tempSessionExpiry, false),  // Temporary session
        Audits.log(user.actor, 'user.session.create', user.actor, {
          userAgent: headers['user-agent'],
          totpSetupRequired: true
        }),
        Users.updateLastLoginAt(user)
      ])
        .then(([ session ]) => ({
          ...session,
          requireTotpSetup: true,  // NEW FLAG for mandatory setup
          mandatory: true           // Indicates cannot dismiss
        }));
    }

    // Not mandatory role, proceed with normal session creation
    return createUserSession({ Audits, Sessions, Users }, headers, user, true)
      .then((middleware) => middleware(_, response))
      .then((session) => {
        // Check if user should be prompted for TOTP enrollment (optional)
        return VgWebUserTotp.shouldPromptEnrollment(user.actorId)
          .then((shouldPrompt) => ({
            ...session,
            shouldPromptTotpEnrollment: shouldPrompt  // Optional prompt flag
          }));
      });
  });
```

#### 1.4 Dismiss Prompt Endpoint

**File:** `server/lib/resources/vg-web-user-totp.js`

Add new endpoint:

```javascript
// POST /v1/users/:id/totp/dismiss-enrollment-prompt
service.post('/users/:id/totp/dismiss-enrollment-prompt', endpoint(async (container, { auth, params, body }) => {
  const { VgWebUserTotp, Users } = container;
  const actorId = parseInt(params.id, 10);

  // User can dismiss their own prompt, or admin can dismiss for others
  await auth.canOrReject('user.update', await Users.getByActorId(actorId).then(getOrNotFound));

  // Check if user's role has mandatory TOTP requirement
  const isMandatory = await VgWebUserTotp.isRoleMandatoryForTotp(actorId);
  if (isMandatory) {
    throw Problem.user.insufficientRights({
      message: 'Cannot dismiss TOTP enrollment for users in roles that require 2FA'
    });
  }

  const { remindAfterDays } = body;  // null = permanent, number = remind later

  if (remindAfterDays !== null && remindAfterDays !== undefined) {
    if (typeof remindAfterDays !== 'number' || remindAfterDays < 1 || remindAfterDays > 365) {
      throw Problem.user.invalidDataTypeOfParameter({ field: 'remindAfterDays', expected: 'number 1-365' });
    }
  }

  await VgWebUserTotp.dismissEnrollmentPrompt(actorId, remindAfterDays);

  return { success: true };
}));
```

#### 1.5 System Settings Endpoint

**File:** `server/lib/resources/vg-settings.js` (or system settings resource)

Add endpoint to get/update mandatory roles:

```javascript
// GET /v1/system/settings/totp-mandatory-roles
service.get('/system/settings/totp-mandatory-roles', endpoint(async (container, { auth }) => {
  await auth.canOrReject('config.read', { system: true });

  const { VgSettings } = container;
  const mandatoryRoles = await VgSettings.get('vg_totp_mandatory_roles');

  return {
    mandatoryRoles: JSON.parse(mandatoryRoles || '["admin"]')
  };
}));

// PUT /v1/system/settings/totp-mandatory-roles
service.put('/system/settings/totp-mandatory-roles', endpoint(async (container, { auth, body }) => {
  await auth.canOrReject('config.set', { system: true });

  const { VgSettings } = container;
  const { mandatoryRoles } = body;

  // Validate: must be array of strings
  if (!Array.isArray(mandatoryRoles) || !mandatoryRoles.every(r => typeof r === 'string')) {
    throw Problem.user.invalidDataTypeOfParameter({
      field: 'mandatoryRoles',
      expected: 'array of role names'
    });
  }

  // Validate: roles must exist in system
  const validRoles = ['admin', 'manager', 'viewer'];  // Get from system config
  const invalidRoles = mandatoryRoles.filter(r => !validRoles.includes(r));
  if (invalidRoles.length > 0) {
    throw Problem.user.invalidDataTypeOfParameter({
      field: 'mandatoryRoles',
      expected: `valid roles: ${validRoles.join(', ')}`,
      got: invalidRoles.join(', ')
    });
  }

  await VgSettings.set('vg_totp_mandatory_roles', JSON.stringify(mandatoryRoles));

  return { success: true };
}));
```

---

### 2. Frontend Changes

#### 2.1 Login Component

**File:** `client/src/components/account/login.vue`

Capture enrollment flags from response:

```javascript
// Around line 232-245 (Phase 1 - no TOTP flow)
.then((response) => {
  const sessionData = response.data;

  if (sessionData && sessionData.requireTotp === true) {
    this.tempSessionToken = sessionData.token;
    this.requiresTotp = true;
    this.disabled = false;
    return;
  }

  // NEW: Check if mandatory TOTP setup is required
  if (sessionData && sessionData.requireTotpSetup === true) {
    // User MUST set up TOTP before proceeding
    this.tempSessionToken = sessionData.token;
    this.requiresTotpSetup = true;
    this.isMandatory = sessionData.mandatory || false;
    this.disabled = false;
    return;  // Show forced setup modal, don't proceed with login
  }

  // No TOTP required, proceed with login
  this.session.data = sessionData;

  // NEW: Store optional enrollment prompt flag for post-login display
  if (sessionData.shouldPromptTotpEnrollment) {
    sessionStorage.setItem('pendingTotpEnrollmentPrompt', 'true');
  }

  return logIn(this.container, true)
    // ... rest of navigation
})
```

**Data properties to add:**
```javascript
data() {
  return {
    // ... existing fields
    requiresTotpSetup: false,  // NEW
    isMandatory: false         // NEW
  };
}
```

#### 2.2 Dashboard/Home Component

**File:** `client/src/components/home.vue` (or wherever user lands after login)

Check for pending enrollment prompt on mount:

```javascript
// In component's mounted() or setup()
mounted() {
  // Check if enrollment prompt is pending
  const shouldPrompt = sessionStorage.getItem('pendingTotpEnrollmentPrompt');
  if (shouldPrompt === 'true') {
    sessionStorage.removeItem('pendingTotpEnrollmentPrompt');
    this.showTotpEnrollmentModal = true;
  }
},

data() {
  return {
    showTotpEnrollmentModal: false
  };
}
```

#### 2.3 Optional Enrollment Prompt Modal

**File:** `client/src/components/vg/vg-totp-enrollment-prompt-modal.vue` (NEW)

```vue
<template>
  <modal v-if="state" @hidden="$emit('hide')">
    <template #title>🔒 {{ $t('title') }}</template>

    <div class="modal-introduction">
      <p>{{ $t('intro') }}</p>
      <ul>
        <li>{{ $t('benefit1') }}</li>
        <li>{{ $t('benefit2') }}</li>
        <li>{{ $t('benefit3') }}</li>
      </ul>
    </div>

    <div class="modal-actions">
      <button type="button" class="btn btn-primary"
        @click="setupNow">
        {{ $t('action.setupNow') }}
      </button>
      <button type="button" class="btn btn-default"
        @click="remindLater">
        {{ $t('action.remindLater') }}
      </button>
      <button type="button" class="btn btn-link"
        @click="dontAskAgain">
        {{ $t('action.dontAsk') }}
      </button>
    </div>
  </modal>
</template>

<script>
import Modal from '../modal.vue';
import { apiPaths } from '../../util/request';

export default {
  name: 'VgTotpEnrollmentPromptModal',
  components: { Modal },
  inject: ['alert'],
  props: {
    state: Boolean,
    userId: Number
  },
  methods: {
    setupNow() {
      this.$emit('setup');
      this.$emit('hide');
    },

    remindLater() {
      this.request({
        method: 'POST',
        url: apiPaths.totpDismissPrompt(this.userId),
        data: { remindAfterDays: 7 }
      })
        .then(() => {
          this.alert.info(this.$t('alert.remindSuccess'));
          this.$emit('hide');
        });
    },

    dontAskAgain() {
      this.request({
        method: 'POST',
        url: apiPaths.totpDismissPrompt(this.userId),
        data: { remindAfterDays: null }
      })
        .then(() => {
          this.$emit('hide');
        });
    }
  }
};
</script>

<i18n lang="json5">
{
  "en": {
    "title": "Secure Your Account with Two-Factor Authentication",
    "intro": "Protect your account with an extra layer of security. Two-factor authentication (2FA) requires a code from your phone in addition to your password.",
    "benefit1": "Prevents unauthorized access even if your password is compromised",
    "benefit2": "Works with Google Authenticator, Authy, and other apps",
    "benefit3": "Takes less than 2 minutes to set up",
    "action": {
      "setupNow": "Set Up 2FA Now",
      "remindLater": "Remind Me in 7 Days",
      "dontAsk": "Don't Ask Again"
    },
    "alert": {
      "remindSuccess": "We'll remind you about 2FA in 7 days"
    }
  }
}
</i18n>
```

#### 2.4 Mandatory Enrollment Modal (NEW)

**File:** `client/src/components/vg/vg-totp-mandatory-setup-modal.vue` (NEW)

```vue
<template>
  <modal v-if="state" :hideable="false">
    <template #title>🔒 {{ $t('title') }}</template>

    <div class="modal-introduction">
      <div class="alert alert-warning">
        <p><strong>{{ $t('mandatory') }}</strong></p>
      </div>
      <p>{{ $t('intro') }}</p>
      <ul>
        <li>{{ $t('step1') }}</li>
        <li>{{ $t('step2') }}</li>
        <li>{{ $t('step3') }}</li>
      </ul>
    </div>

    <div class="modal-actions">
      <button type="button" class="btn btn-primary btn-block"
        @click="beginSetup">
        {{ $t('action.begin') }}
      </button>
      <p class="text-muted text-center" style="margin-top: 10px;">
        {{ $t('cannotDismiss') }}
      </p>
    </div>
  </modal>
</template>

<script>
import Modal from '../modal.vue';

export default {
  name: 'VgTotpMandatorySetupModal',
  components: { Modal },
  props: {
    state: Boolean,
    userId: Number
  },
  methods: {
    beginSetup() {
      this.$emit('begin-setup');
    }
  }
};
</script>

<i18n lang="json5">
{
  "en": {
    "title": "Two-Factor Authentication Required",
    "mandatory": "Your account requires 2FA to be enabled before you can access the system.",
    "intro": "Two-factor authentication adds an extra layer of security to your account. You'll need an authenticator app on your phone.",
    "step1": "Scan the QR code with your authenticator app",
    "step2": "Enter the 6-digit code to verify",
    "step3": "Save your backup codes in a secure location",
    "action": {
      "begin": "Set Up 2FA Now"
    },
    "cannotDismiss": "You must complete this setup to continue."
  }
}
</i18n>
```

#### 2.5 System Settings UI (Admin Configuration)

**File:** `client/src/components/system/vg-totp-settings.vue` (NEW)

```vue
<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <h4>{{ $t('title') }}</h4>
    </div>
    <div class="panel-body">
      <p>{{ $t('description') }}</p>

      <form @submit.prevent="save">
        <div class="checkbox" v-for="role in availableRoles" :key="role.id">
          <label>
            <input type="checkbox"
              :value="role.id"
              v-model="mandatoryRoles"
              :disabled="saving">
            {{ role.displayName }}
          </label>
          <p class="help-block">{{ role.description }}</p>
        </div>

        <button type="submit" class="btn btn-primary" :disabled="saving">
          {{ saving ? $t('action.saving') : $t('action.save') }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import { apiPaths } from '../../util/request';

export default {
  name: 'VgTotpSettings',
  data() {
    return {
      mandatoryRoles: [],
      availableRoles: [
        {
          id: 'admin',
          displayName: 'Administrator',
          description: 'Full system access and configuration'
        },
        {
          id: 'manager',
          displayName: 'Project Manager',
          description: 'Can manage projects and users'
        },
        {
          id: 'viewer',
          displayName: 'Viewer',
          description: 'Read-only access to projects'
        }
      ],
      saving: false
    };
  },
  created() {
    this.fetchSettings();
  },
  methods: {
    fetchSettings() {
      this.request({
        method: 'GET',
        url: '/v1/system/settings/totp-mandatory-roles'
      })
        .then(({ data }) => {
          this.mandatoryRoles = data.mandatoryRoles;
        });
    },
    save() {
      this.saving = true;
      this.request({
        method: 'PUT',
        url: '/v1/system/settings/totp-mandatory-roles',
        data: { mandatoryRoles: this.mandatoryRoles }
      })
        .then(() => {
          this.alert.success(this.$t('alert.success'));
          this.saving = false;
        })
        .catch(() => {
          this.saving = false;
        });
    }
  }
};
</script>

<i18n lang="json5">
{
  "en": {
    "title": "Mandatory 2FA Roles",
    "description": "Select which user roles must have Two-Factor Authentication enabled. Users in these roles will be required to set up 2FA before they can access the system.",
    "action": {
      "save": "Save Settings",
      "saving": "Saving..."
    },
    "alert": {
      "success": "Mandatory 2FA roles updated successfully"
    }
  }
}
</i18n>
```

---

## Critical Files

### Backend
- `server/lib/model/migrations/20260208-01-totp-enrollment-prompts.sql` (NEW - DB schema + system setting)
- `server/lib/model/query/vg-web-user-totp.js` (MODIFY - add 3 methods: isRoleMandatoryForTotp, shouldPromptEnrollment, dismissEnrollmentPrompt)
- `server/lib/resources/sessions.js` (MODIFY - add mandatory role check and enrollment logic)
- `server/lib/resources/vg-web-user-totp.js` (MODIFY - add dismiss endpoint with mandatory check)
- `server/lib/resources/vg-settings.js` (MODIFY - add GET/PUT endpoints for mandatory roles)

### Frontend
- `client/src/components/account/login.vue` (MODIFY - capture requireTotpSetup flag)
- `client/src/components/home.vue` (MODIFY - show appropriate modal based on mandatory vs optional)
- `client/src/components/vg/vg-totp-enrollment-prompt-modal.vue` (NEW - optional prompt with dismiss)
- `client/src/components/vg/vg-totp-mandatory-setup-modal.vue` (NEW - forced setup, no dismiss)
- `client/src/components/system/vg-totp-settings.vue` (NEW - admin UI for mandatory roles)
- `client/src/util/request.js` (MODIFY - add API paths)

---

## Testing Plan

### Manual Testing

#### Optional Enrollment (Non-Mandatory Roles)

1. **First-time login (never prompted):**
   - Login as non-admin user without 2FA
   - Verify optional modal appears on home page
   - Click "Set Up Now" → TOTP setup modal opens
   - Complete setup → verify prompt doesn't appear again

2. **Remind later:**
   - Login as non-admin user without 2FA
   - Click "Remind Me in 7 Days"
   - Login again immediately → no prompt
   - Fast-forward system time 8 days (or wait) → prompt appears again

3. **Permanent dismissal:**
   - Login as non-admin user without 2FA
   - Click "Don't Ask Again"
   - Login multiple times → never see prompt again

4. **Users with 2FA enabled:**
   - Login with 2FA
   - Complete TOTP verification
   - Verify no enrollment prompt (already enrolled)

#### Mandatory Enrollment (Admin and Configured Roles)

5. **Admin login without 2FA:**
   - Login as admin user without 2FA
   - Verify MANDATORY modal appears (non-dismissible)
   - Modal should have NO "Remind later" or "Don't ask again" buttons
   - Cannot close modal or navigate away
   - Click "Set Up 2FA Now" → TOTP setup flow begins
   - Complete QR scan and verification
   - After setup, login flow continues with normal TOTP verification

6. **User promoted to mandatory role:**
   - User with "viewer" role (non-mandatory) logs in → optional prompt
   - Admin changes system setting to make "viewer" a mandatory role
   - User logs out and logs in again
   - Now sees MANDATORY modal (cannot dismiss)

7. **Attempt to dismiss mandatory prompt via API:**
   - Login as admin without 2FA
   - Try to call `/users/:id/totp/dismiss-enrollment-prompt` via API
   - Should return 403 error: "Cannot dismiss for mandatory roles"

#### Admin Configuration

8. **Configure mandatory roles:**
   - Login as admin
   - Navigate to System Settings → 2FA Settings
   - Check/uncheck roles (admin, manager, viewer)
   - Save settings
   - Verify setting saved to database
   - Logout and login as user in newly configured mandatory role
   - Verify mandatory modal appears

### Edge Cases

- User closes browser during mandatory setup → On return, forced to complete setup
- User navigates away before modal shows → flag persists, modal appears
- Admin editing another user → enrollment prompt logic doesn't break
- Role changed while user is logged in → Check on next login, not during session
- Multiple tabs open → Modal appears in all tabs (sessionStorage shared)

---

## Security Considerations

- ✅ Prompt is informational only, never blocks access
- ✅ Users can permanently opt out
- ✅ No PII stored in prompt tracking
- ✅ Dismissal requires authentication
- ✅ Database indexes prevent performance impact

---

## Future Enhancements (Out of Scope)

- Admin dashboard showing 2FA adoption rate
- Configurable reminder intervals
- Different prompt strategies (banner vs modal)
- Email reminders for 2FA enrollment
