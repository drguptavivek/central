# Web User Security Enhancement: API Tokens + Service Accounts

> **Created:** 2026-02-08
> **Updated:** 2026-02-09 (Revised approach)
> **Status:** SUPERSEDED - See /home/vivek/.claude/plans/twinkly-marinating-beacon.md
> **Priority:** High (Security Enhancement)

---

## ⚠️ IMPORTANT UPDATE (2026-02-09)

**This plan has been revised and expanded.** The new comprehensive plan is located at:
`/home/vivek/.claude/plans/twinkly-marinating-beacon.md`

**Key Changes:**
1. **Added API Token Management** - For human laptop users (Jupyter, dynamic IPs)
2. **Refined Service Accounts** - For automated systems (CI/CD, static IPs)
3. **Clarified Scope** - Web users only, app users untouched, OpenRosa unchanged
4. **VG Modularity** - API-first TDD workflow, core edits minimized and documented

**Continue reading for original context, then refer to new plan for implementation details.**

---

## Problem Statement (Original)

**Current Security Gap:**
- Web user bearer tokens bypass TOTP checks (by design for automation)
- No distinction between human laptop users and automated service accounts
- Same 24-hour token lifetime for all use cases
- No mandatory IP restrictions for programmatic access
- Audit logs don't distinguish service account vs human activity

**Risk:**
- Stolen service account token = 24 hours of unauthorized access
- Service accounts can access from anywhere (no IP restriction)
- No way to enforce stricter policies for automation accounts
- Hard to track/audit programmatic API usage separately

**Use Cases (Revised):**

1. **Human Laptop Users** (researchers, analysts):
   - Run pyodk scripts from Jupyter notebooks
   - Travel frequently, dynamic IPs (home ISP rotation, VPNs)
   - Need: Long-lived tokens created via TOTP-protected UI
   - Don't need: IP whitelist enforcement (mobility required)

2. **Automated Service Accounts** (CI/CD, cron jobs):
   - Run from servers with static IPs
   - Need: Mandatory IP whitelist, shorter sessions
   - Need: Clear audit trail

---

## Revised Solution (2026-02-09)

**TWO Complementary Systems:**

### 1. API Token Management (NEW)
- Human users create long-lived tokens (30-365 days) via TOTP-protected UI
- Tokens work from any IP (no whitelist enforcement for regular users)
- Revocable, trackable, displayed once
- Pattern: GitHub Personal Access Tokens

### 2. Service Account Flag (ENHANCED)
- Mark users as "service accounts" (automated systems)
- Mandatory IP whitelist for ALL auth methods (tokens + sessions)
- Shorter session lifetime (1 hour vs 24 hours)
- Clear audit logging (serviceAccount: true)

**Benefits:**
- ✅ Human laptop users: Create tokens in UI, use from anywhere
- ✅ Service accounts: Mandatory IP whitelist, shorter exposure window
- ✅ Clear separation: human vs automation
- ✅ No breaking changes to app users or OpenRosa

---

## CRITICAL CONSTRAINTS (Added 2026-02-09)

**MUST NOT CHANGE:**
- ❌ App user authentication (linked to MEDRES-ODK-Collect fork)
- ❌ OpenRosa protocol (used by ODK Collect)
- ❌ Field key authentication

**CAN CHANGE:**
- ✅ Web user authentication (API tokens, service accounts)
- ✅ Web UI (token management, service account settings)

**OUT OF SCOPE:**
- pyodk compatibility (future separate project)

---

## Current State Analysis

### Code Locations

**Authentication Flow:**
- `server/lib/http/preprocessors.js:99-109` - authBySessionToken()
  - `isCookie=true` → checkTotpVerification()
  - `isCookie=false` → checkIpWhitelist() only

**Key Finding:**
```javascript
const authBySessionToken = (token, isCookie = false) => {
  return Sessions.getByBearerToken(token)
    .then((cxt) => {
      if (isCookie) {
        return checkTotpVerification(...);  // Web UI only
      }
      return checkIpWhitelist(...);  // Bearer tokens - no TOTP
    });
}
```

**Existing VG Features:**
- IP whitelist system (`vg_user_ip_whitelist` table)
- Currently optional for web users
- Not enforced for service accounts

---

## Solution Overview (See Full Plan for Details)

**Implementation Structure:**

### Part 1: API Token Management
- New table: `vg_api_tokens`
- Token format: `vg_tkn_<random>_<checksum>`
- Created via TOTP-protected UI
- NOT subject to IP whitelist (for regular users)
- Revocable, trackable

### Part 2: Service Account System
- New column: `users.is_service_account`
- Mandatory IP whitelist enforcement
- 1-hour session lifetime
- Audit flag: `serviceAccount: true`

### Part 3: Integration
- Detect API tokens in preprocessors.js (vg_tkn_ prefix)
- Service accounts: enforce IP for both tokens AND sessions
- Regular users: optional IP whitelist

---

## Implementation Plan

### Phase 1: Database Schema

#### Add Service Account Flag

```sql
-- Migration: 20260208-01-add-service-account-flag.js

exports.up = (knex) => knex.schema.table('users', (table) => {
  table.boolean('is_service_account').defaultTo(false).notNull();
  table.timestamp('service_account_marked_at');
});

exports.down = (knex) => knex.schema.table('users', (table) => {
  table.dropColumn('is_service_account');
  table.dropColumn('service_account_marked_at');
});
```

**Fields:**
- `is_service_account` - Boolean flag (default false)
- `service_account_marked_at` - When user was marked as service account

---

### Phase 2: Backend Changes

#### 2.1 Add Service Account Detection

**File:** `server/lib/model/frames/user.js`

```javascript
// Add to User frame
isServiceAccount() {
  return this.aux.data.isServiceAccount === true;
}
```

**File:** `server/lib/model/query/users.js`

```javascript
// Update getByEmail to include is_service_account
const getByEmail = (email) => ({ maybeOne }) =>
  maybeOne(sql`
    SELECT users.*, actors.*,
      users.is_service_account AS "isServiceAccount",
      users.service_account_marked_at AS "serviceAccountMarkedAt"
    FROM users
    INNER JOIN actors ON actors.id = users."actorId"
    WHERE lower(users.email) = lower(${email})
      AND actors."deletedAt" IS NULL
  `).then(map(construct(User)));
```

#### 2.2 Enforce Mandatory IP Whitelist

**File:** `server/lib/http/preprocessors.js`

```javascript
// Modify checkIpWhitelist function (lines 68-97)
const checkIpWhitelist = (session, cxt) => {
  // Only check for user (web user) bearer tokens
  if (session.actor.type !== 'user') {
    return Promise.resolve(cxt);
  }

  const clientIp = getClientIp(request);
  if (!clientIp) {
    return Promise.resolve(cxt); // Allow if we can't determine IP
  }

  // NEW: Check if this is a service account
  return Users.getById(session.actor.id)
    .then(getOrElse(null))
    .then((user) => {
      if (user == null) return cxt;

      const isServiceAccount = user.isServiceAccount();

      // Check if user has IP whitelist entries
      return VgUserIpWhitelist.hasAnyEntries(session.actor.id)
        .then((hasEntries) => {
          // MANDATORY for service accounts
          if (isServiceAccount && !hasEntries) {
            throw Problem.user.insufficientRights({
              message: 'Service accounts must have IP whitelist configured'
            });
          }

          // If no whitelist, allow (for regular users)
          if (!hasEntries) {
            return cxt;
          }

          // Check if IP is whitelisted
          return VgUserIpWhitelist.isIpWhitelisted(session.actor.id, clientIp)
            .then((whitelisted) => {
              if (!whitelisted) {
                throw Problem.user.insufficientRights({
                  message: 'Access denied: IP not whitelisted'
                });
              }
              return cxt;
            });
        });
    });
};
```

#### 2.3 Adjust Token Lifetime for Service Accounts

**File:** `server/lib/resources/sessions.js`

```javascript
// Modify session creation (around line 136)
const createSession = (user) => {
  // Service accounts: 1 hour, Regular users: 24 hours
  const sessionLifetime = user.isServiceAccount()
    ? 3600        // 1 hour
    : 86400;      // 24 hours (default)

  const expiresAt = new Date(Date.now() + sessionLifetime * 1000);

  return Sessions.create(user.actor, expiresAt, totpVerified);
};
```

#### 2.4 Enhanced Audit Logging

**File:** `server/lib/model/audits.js`

```javascript
// Add service account flag to audit logs
const log = (actor, action, actee, details) => {
  const logDetails = { ...details };

  // If actor is a service account, add flag
  if (actor && actor.aux?.data?.isServiceAccount) {
    logDetails.serviceAccount = true;
  }

  return _log(actor, action, actee, logDetails);
};
```

---

### Phase 3: Admin UI Changes

#### 3.1 Mark User as Service Account

**File:** `client/src/components/user/edit.vue`

```vue
<template>
  <div class="user-edit">
    <!-- Existing fields... -->

    <!-- NEW: Service Account Toggle -->
    <form-group v-if="canManageServiceAccounts">
      <label class="checkbox-label">
        <input
          v-model="formData.isServiceAccount"
          type="checkbox"
          :disabled="!canEdit"
        >
        <span>Mark as Service Account (API automation)</span>
      </label>
      <p class="help-block">
        Service accounts:
        • Get 1-hour tokens (instead of 24 hours)
        • MUST have IP whitelist configured
        • Appear separately in audit logs
      </p>
    </form-group>

    <!-- Show warning if service account without IP whitelist -->
    <alert
      v-if="formData.isServiceAccount && !hasIpWhitelist"
      type="warning"
    >
      ⚠️ Service accounts require IP whitelist configuration.
      <router-link :to="ipWhitelistRoute">
        Configure IP whitelist →
      </router-link>
    </alert>
  </div>
</template>
```

#### 3.2 IP Whitelist Management UI

**Enhance:** `client/src/components/vg-user-ip-whitelist.vue`

```vue
<template>
  <div class="ip-whitelist-manager">
    <h3>IP Whitelist</h3>

    <!-- Show if service account -->
    <alert v-if="user.isServiceAccount" type="info">
      🔒 This is a service account. IP whitelist is MANDATORY.
    </alert>

    <!-- Existing IP whitelist UI -->
    <ip-whitelist-entries
      :user-id="userId"
      :required="user.isServiceAccount"
    />
  </div>
</template>
```

---

### Phase 4: API Endpoints

#### 4.1 Admin Endpoint: Mark as Service Account

**File:** `server/lib/resources/users.js`

```javascript
service.patch('/v1/users/:id/service-account', endpoint(({ Users, Audits }, { auth, params, body }) =>
  Users.getById(params.id)
    .then(getOrNotFound)
    .then((user) => auth.canOrReject('user.update', user)
      .then(() => {
        const { isServiceAccount } = body;

        if (typeof isServiceAccount !== 'boolean') {
          throw Problem.user.invalidDataTypeOfParameter({
            field: 'isServiceAccount',
            expected: 'boolean'
          });
        }

        return Users.update(user, {
          isServiceAccount,
          serviceAccountMarkedAt: isServiceAccount ? new Date() : null
        })
          .then(() => Audits.log(auth.actor(), 'user.update', user.actor, {
            serviceAccount: isServiceAccount,
            field: 'is_service_account'
          }))
          .then(() => ({ success: true }));
      })
    )
));
```

#### 4.2 Get Service Account Status

**File:** `server/lib/resources/users.js`

```javascript
// Add to existing GET /v1/users/:id response
service.get('/v1/users/:id', endpoint(({ Users }, { auth, params }) =>
  Users.getById(params.id)
    .then(getOrNotFound)
    .then((user) => auth.canOrReject('user.read', user)
      .then(() => {
        const response = user.forApi();
        // Add service account fields
        response.isServiceAccount = user.isServiceAccount();
        response.serviceAccountMarkedAt = user.aux.data.serviceAccountMarkedAt;
        return response;
      })
    )
));
```

---

### Phase 5: Testing

#### 5.1 Unit Tests

**File:** `server/test/unit/http/preprocessors.js`

```javascript
describe('checkIpWhitelist for service accounts', () => {
  it('should require IP whitelist for service accounts', async () => {
    const serviceUser = await createUser({ isServiceAccount: true });
    const session = await createSession(serviceUser);

    // Should reject if no whitelist entries
    await assert.rejects(
      checkIpWhitelist(session, context),
      /Service accounts must have IP whitelist/
    );
  });

  it('should allow service accounts with valid IP', async () => {
    const serviceUser = await createUser({ isServiceAccount: true });
    await createIpWhitelist(serviceUser.id, '192.168.1.100');
    const session = await createSession(serviceUser);

    // Should succeed if IP matches
    const result = await checkIpWhitelist(session, contextWithIp('192.168.1.100'));
    result.should.be.ok();
  });

  it('should reject service accounts from non-whitelisted IP', async () => {
    const serviceUser = await createUser({ isServiceAccount: true });
    await createIpWhitelist(serviceUser.id, '192.168.1.100');
    const session = await createSession(serviceUser);

    // Should reject if IP doesn't match
    await assert.rejects(
      checkIpWhitelist(session, contextWithIp('10.0.0.1')),
      /Access denied: IP not whitelisted/
    );
  });
});
```

#### 5.2 Integration Tests

**File:** `server/test/integration/api/vg-service-accounts.js`

```javascript
describe('api: service accounts', () => {
  it('should create 1-hour tokens for service accounts', testService(async (service, container) => {
    const serviceUser = await createUser(container, { isServiceAccount: true });

    const response = await service.post('/v1/sessions')
      .send({ email: serviceUser.email, password: 'password' })
      .expect(200);

    const expiresAt = new Date(response.body.expiresAt);
    const now = new Date();
    const diffHours = (expiresAt - now) / (1000 * 60 * 60);

    // Should be ~1 hour, not 24 hours
    diffHours.should.be.approximately(1, 0.1);
  }));

  it('should enforce IP whitelist for service account API calls', testService(async (service, container) => {
    const serviceUser = await createUser(container, { isServiceAccount: true });
    await createIpWhitelist(container, serviceUser.id, '192.168.1.100');

    const token = await getToken(service, serviceUser);

    // From whitelisted IP - should work
    await service.get('/v1/projects')
      .set('Authorization', `Bearer ${token}`)
      .set('X-Forwarded-For', '192.168.1.100')
      .expect(200);

    // From non-whitelisted IP - should fail
    await service.get('/v1/projects')
      .set('Authorization', `Bearer ${token}`)
      .set('X-Forwarded-For', '10.0.0.1')
      .expect(403);
  }));

  it('should log service account flag in audits', testService(async (service, container) => {
    const serviceUser = await createUser(container, { isServiceAccount: true });
    const token = await getToken(service, serviceUser);

    await service.get('/v1/projects')
      .set('Authorization', `Bearer ${token}`)
      .set('X-Forwarded-For', '192.168.1.100')
      .expect(200);

    const audit = await container.one(sql`
      SELECT details FROM audits
      WHERE action = 'project.list'
        AND "actorId" = ${serviceUser.actorId}
      ORDER BY "loggedAt" DESC
      LIMIT 1
    `);

    audit.details.serviceAccount.should.equal(true);
  }));
});
```

#### 5.3 pyodk Compatibility Test

**File:** `server/test/integration/pyodk-compatibility.js`

```javascript
describe('pyodk compatibility', () => {
  it('should work with pyodk authentication flow', testService(async (service, container) => {
    const serviceUser = await createUser(container, {
      isServiceAccount: true,
      email: 'pyodk-test@example.com'
    });
    await createIpWhitelist(container, serviceUser.id, '127.0.0.1');

    // Simulate pyodk login
    const loginResponse = await service.post('/v1/sessions')
      .set('X-Forwarded-For', '127.0.0.1')
      .send({
        email: 'pyodk-test@example.com',
        password: 'password'
      })
      .expect(200);

    const token = loginResponse.body.token;

    // Simulate pyodk API calls
    await service.get('/v1/projects')
      .set('Authorization', `Bearer ${token}`)
      .set('X-Forwarded-For', '127.0.0.1')
      .expect(200);

    await service.get('/v1/projects/1/forms')
      .set('Authorization', `Bearer ${token}`)
      .set('X-Forwarded-For', '127.0.0.1')
      .expect(200);
  }));
});
```

---

### Phase 6: Documentation

#### 6.1 Admin Guide

**File:** `docs/vg/vg-server/service-accounts-guide.md`

```markdown
# Service Account Guide

## What are Service Accounts?

Service accounts are web user accounts used for programmatic API access:
- pyodk scripts
- CI/CD pipelines
- Data export automation
- Integration with other systems

## Security Features

1. **Mandatory IP Whitelist**: Must configure allowed IPs
2. **Shorter Tokens**: 1-hour expiry instead of 24 hours
3. **Separate Auditing**: Clearly marked in logs

## Creating a Service Account

### Step 1: Create Web User
Create a regular web user account via admin UI

### Step 2: Mark as Service Account
1. Go to User Settings
2. Check "Mark as Service Account"
3. Save

### Step 3: Configure IP Whitelist
1. Go to User IP Whitelist
2. Add allowed IP addresses (CIDR notation supported)
3. Example: `192.168.1.0/24` or `10.0.0.50`

### Step 4: Use with pyodk

```python
from pyodk.client import Client

client = Client(
    base_url="https://central.example.com",
    username="service@example.com",
    password="SecureServicePass!123"
)

# Token automatically obtained and used
projects = client.projects.list()
```

## Best Practices

1. **Use dedicated accounts**: Don't reuse human user accounts
2. **Minimal permissions**: Assign lowest role needed (viewer, not admin)
3. **Rotate passwords**: Change service account passwords regularly
4. **Monitor usage**: Check audit logs for unusual activity
5. **Document purpose**: Name accounts clearly (e.g., "CI/CD Pipeline", "Daily Export Script")

## Troubleshooting

### "Service accounts must have IP whitelist configured"
→ Add at least one IP address to the whitelist

### "Access denied: IP not whitelisted"
→ Add your server's IP to the whitelist (check X-Forwarded-For header)

### Token expires too quickly
→ Service accounts use 1-hour tokens (by design). pyodk handles re-authentication automatically.
```

#### 6.2 Update Authentication Documentation

**File:** `docs/vg/web-vs-upstream-app-user-vs-vg-app-user-auth.md`

Add section:
```markdown
## Service Account Security (NEW)

As of 2026-02-08, service accounts have enhanced security:

**Mandatory Features:**
- ✅ IP whitelist required (cannot be empty)
- ✅ 1-hour token lifetime (reduces exposure)
- ✅ Separate audit logging (serviceAccount: true flag)

**Setup Required:**
1. Mark user as service account in admin UI
2. Configure IP whitelist (minimum 1 entry)
3. Use pyodk or bearer token as usual

**Security Benefits:**
- Stolen token only valid 1 hour (not 24)
- Can only be used from whitelisted IPs
- Clear audit trail distinguishes automation from humans
```

---

## Migration Path

### For Existing Deployments

#### Option A: Opt-In (Recommended)
```sql
-- No automatic migration
-- Admins manually mark service accounts via UI
-- Existing users continue working (backward compatible)
```

#### Option B: Auto-Detect Service Accounts
```sql
-- Identify likely service accounts by usage patterns
UPDATE users
SET is_service_account = true
WHERE email IN (
  SELECT DISTINCT email
  FROM audits a
  JOIN users u ON u."actorId" = a."actorId"
  WHERE a.details->>'userAgent' LIKE '%python%'
    OR a.details->>'userAgent' LIKE '%pyodk%'
    OR a.action LIKE '%.list%'
  GROUP BY email
  HAVING COUNT(*) > 100  -- High API usage
);
```

#### Option C: Gradual Rollout
```sql
-- Phase 1: Add flag, don't enforce (logging only)
-- Phase 2: Enforce for newly marked accounts
-- Phase 3: Email admins about unmarked high-usage accounts
-- Phase 4: Auto-mark based on usage patterns
```

**Recommendation:** Option A (Opt-In) for safety

---

## Rollout Plan

### Week 1: Database & Backend
- [ ] Create migration (service account flag)
- [ ] Update User model
- [ ] Modify checkIpWhitelist enforcement
- [ ] Adjust token lifetime logic
- [ ] Write unit tests
- [ ] Write integration tests

### Week 2: Admin UI
- [ ] Add service account checkbox to user edit
- [ ] Show IP whitelist warning
- [ ] Update IP whitelist UI
- [ ] Add API endpoints
- [ ] Frontend tests

### Week 3: Testing & Documentation
- [ ] pyodk compatibility testing
- [ ] Security testing
- [ ] Write admin guide
- [ ] Update API docs
- [ ] Create migration guide

### Week 4: Rollout
- [ ] Deploy to staging
- [ ] Test with real pyodk scripts
- [ ] Deploy to production
- [ ] Monitor logs
- [ ] Gather feedback

---

## Success Metrics

**Security:**
- [ ] 100% of service accounts have IP whitelist
- [ ] Service account tokens limited to 1 hour
- [ ] Clear audit trail (serviceAccount flag present)

**Compatibility:**
- [ ] pyodk scripts work without code changes
- [ ] No reports of broken automation
- [ ] Token refresh handled automatically

**Adoption:**
- [ ] Admins mark known service accounts
- [ ] Documentation clear and complete
- [ ] Support requests minimal

---

## Future Enhancements

### Phase 2 (Optional):
- [ ] API key system (long-lived, separate from sessions)
- [ ] Per-key permissions (subset of user's access)
- [ ] Key rotation mechanism
- [ ] Key usage dashboard

### Phase 3 (Optional):
- [ ] Rate limiting per service account
- [ ] Quota management (X requests/day)
- [ ] Anomaly detection (unusual usage patterns)
- [ ] Webhook notifications on suspicious activity

---

## References

- **Code Review**: `docs/vg/web-vs-upstream-app-user-vs-vg-app-user-auth.md`
- **IP Whitelist**: `docs/vg/vg-server/vg_ip_whitelist_admin_guide.md`
- **pyodk**: https://github.com/getodk/pyodk
- **Preprocessors**: `server/lib/http/preprocessors.js:68-97`

---

## Questions / Decisions Needed

1. **Token lifetime**: 1 hour for service accounts? (vs 30 min, 2 hours)
2. **Migration strategy**: Opt-in vs auto-detect?
3. **Enforcement timing**: Immediate or grace period?
4. **IP whitelist UI**: Existing vs new dedicated page?
5. **Audit log format**: Current structure sufficient?

---

## Approval

- [ ] Security review
- [ ] Architecture review
- [ ] UX review (admin UI)
- [ ] Testing plan approved
- [ ] Documentation review
- [ ] Ready for implementation
