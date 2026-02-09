# ODK Central Security Enhancement: API Token Management & Service Accounts

> **Plan Created:** 2026-02-09
> **Status:** Ready for Review
> **Priority:** High (Security Enhancement)

---

## Context

**Problem:** The existing service account security plan (plan/service-account-security.md) assumes all API users are automated systems on servers with static IPs. However, **many real users are researchers running pyodk in Jupyter notebooks on laptops** with dynamic IPs (travel, home ISP rotation, VPNs).

**Current State:**
- Web users authenticate via POST /v1/sessions → get 24hr bearer token
- Bearer tokens bypass TOTP (by design for automation)
- No distinction between human laptop users vs server automation
- Optional IP whitelist exists but not enforced

**User Requirements:**
1. **Human laptop users** (researchers, analysts):
   - Run pyodk scripts from dynamic IPs
   - Need: Create tokens via TOTP-protected UI, use from anywhere

2. **Server automation** (CI/CD, cron jobs):
   - Run from static IPs
   - Need: Mandatory IP whitelist, shorter token lifetime, strict controls

**Solution:** Implement TWO complementary systems:
- **API Token Management** - Long-lived tokens created via TOTP-protected UI
- **Service Account Flag** - Mandatory IP whitelist for automated systems

---

## CRITICAL CONSTRAINTS

**MUST NOT CHANGE:**
- ❌ **App User Authentication** - Linked to MEDRES-ODK-Collect fork, cannot be modified
- ❌ **OpenRosa Protocol** - Used by ODK Collect, must remain unchanged
- ❌ **Field Key Authentication** - Collect device authentication, must work as-is
- ❌ **App User Routes** - `/projects/:projectId/app-users/*` (project-scoped, separate concern)

**CAN CHANGE:**
- ✅ **Web User Authentication** - API tokens, service accounts (scope of this plan)
- ✅ **Web User Routes** - `/v1/users/:id/*` (system-wide scope)
- ✅ **Web UI** - Token management, service account settings

**OUT OF SCOPE:**
- pyodk compatibility (future separate project)
- App user workflows (no changes to project-scoped routes)
- ODK Collect integration (OpenRosa unchanged)

---

## Route Scope Separation (CRITICAL)

This plan ONLY affects **web user routes** (system-wide scope):
```
/v1/users/:id/api-tokens          ← NEW (web users only)
/v1/users/:id/service-account     ← NEW (web users only)
/v1/users/:id/totp/*               ← Existing (web users only)
/v1/users/:id/ip-whitelist         ← Existing (web users only)
/v1/sessions                       ← Modified (web users only)
```

**App user routes remain UNCHANGED** (project-scoped):
```
/projects/:projectId/app-users                    ← NO CHANGES
/projects/:projectId/app-users/login              ← NO CHANGES
/projects/:projectId/app-users/:id/sessions       ← NO CHANGES
/projects/:projectId/app-users/:id/password/*     ← NO CHANGES
```

**Key Differences:**
| Feature | Web Users | App Users |
|---------|-----------|-----------|
| **Scope** | System-wide (`/v1/users/:id`) | Project-scoped (`/projects/:pid/app-users/:id`) |
| **Actor Type** | `user` | `field_key` |
| **API Tokens** | ✅ YES (this plan) | ❌ NO (not applicable) |
| **Service Accounts** | ✅ YES (this plan) | ❌ NO (not applicable) |
| **IP Whitelist** | ✅ YES (optional for regular, mandatory for service) | ❌ NO (bypassed) |
| **TOTP** | ✅ YES | ❌ NO |
| **Use Case** | Admin/automation | Mobile data collection |

**Pattern to Follow:**
- App users: Like existing `docs/vg/vg-server/routes/app-users.md`
- Web users: Like existing `docs/vg/vg-server/routes/web-user-totp.md`
- **This plan follows web user pattern exclusively**

---

## Design Overview

### Three-Tier Authentication Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Types                      │
├─────────────────────────────────────────────────────────────┤
│ 1. Sessions (Short-Lived)                                   │
│    - Created by POST /v1/sessions (email/password)          │
│    - 24hr lifetime (regular users)                           │
│    - 1hr lifetime (service accounts) ← NEW                   │
│    - Used via cookies OR bearer tokens                       │
│                                                               │
│ 2. API Tokens (Long-Lived) ← NEW SYSTEM                     │
│    - Created via TOTP-protected UI                           │
│    - 30-90 day lifetime (configurable)                       │
│    - Used ONLY as bearer tokens (no cookies)                 │
│    - Revocable by user or admin                              │
│                                                               │
│ 3. Service Account Flag ← NEW SYSTEM                        │
│    - Applies to user account (not token/session)             │
│    - Enforces: mandatory IP whitelist                        │
│    - Affects: both sessions AND API tokens                   │
│    - Clear audit trail (serviceAccount: true)                │
└─────────────────────────────────────────────────────────────┘
```

### How They Work Together

| User Type | Use Sessions? | Use API Tokens? | IP Whitelist | Use Case |
|-----------|---------------|-----------------|--------------|----------|
| **Regular Human** | Yes (24hr) | Yes (90d) | Optional | Web UI + occasional scripts |
| **Researcher (laptop)** | Yes (24hr) | **YES (90d)** | **Not enforced** | Jupyter notebooks with pyodk |
| **Service Account** | Yes (1hr) | Yes (90d) | **MANDATORY** | CI/CD, cron jobs, dashboards |

**Key Decision**: API tokens created by human users are NOT subject to IP whitelist (allows travel). Only service accounts have mandatory IP whitelist for ALL authentication methods.

---

## Part 1: API Token Management System

### Database Schema

**Migration Files:** `server/lib/model/migrations/20260209-01-vg-api-tokens.{js,up.sql,down.sql}`

**File: 20260209-01-vg-api-tokens.up.sql**
```sql
-- VG: API Token Management
-- Create tables for long-lived API tokens (separate from sessions)

BEGIN;

-- Main token table
CREATE TABLE vg_api_tokens (
  id BIGSERIAL PRIMARY KEY,
  "actorId" INTEGER NOT NULL REFERENCES users("actorId") ON DELETE CASCADE,

  -- Token identification
  token TEXT NOT NULL UNIQUE,          -- bcrypt hashed (like passwords)
  token_prefix TEXT NOT NULL,          -- First 8 chars for display (e.g., "vg_tkn_abc...")

  -- Metadata
  name TEXT NOT NULL,                  -- User-provided name
  description TEXT NULL,

  -- Lifecycle
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  last_used_at TIMESTAMPTZ NULL,

  -- Revocation
  revoked_at TIMESTAMPTZ NULL,
  revoked_by INTEGER NULL REFERENCES users("actorId"),

  -- Security tracking
  created_from_ip TEXT NULL,
  created_user_agent TEXT NULL
);

-- Indexes for performance
CREATE INDEX idx_vg_api_tokens_actor ON vg_api_tokens ("actorId");
CREATE INDEX idx_vg_api_tokens_token ON vg_api_tokens (token);
CREATE INDEX idx_vg_api_tokens_prefix ON vg_api_tokens (token_prefix);
CREATE INDEX idx_vg_api_tokens_expires ON vg_api_tokens (expires_at) WHERE revoked_at IS NULL;

-- Token usage tracking (for audit/monitoring)
CREATE TABLE vg_api_token_usage (
  id BIGSERIAL PRIMARY KEY,
  token_id BIGINT NOT NULL REFERENCES vg_api_tokens(id) ON DELETE CASCADE,
  used_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ip TEXT NULL,
  user_agent TEXT NULL,
  endpoint TEXT NULL,
  method TEXT NULL
);

CREATE INDEX idx_vg_token_usage_token_time ON vg_api_token_usage (token_id, used_at DESC);

COMMIT;
```

**File: 20260209-01-vg-api-tokens.down.sql**
```sql
-- VG: Rollback API Token Management

BEGIN;

DROP TABLE IF EXISTS vg_api_token_usage;
DROP TABLE IF EXISTS vg_api_tokens;

COMMIT;
```

**File: 20260209-01-vg-api-tokens.js**
```javascript
// VG: API Token Management
const up = (knex) => knex.raw(require('fs').readFileSync(__dirname + '/20260209-01-vg-api-tokens.up.sql', 'utf8'));
const down = (knex) => knex.raw(require('fs').readFileSync(__dirname + '/20260209-01-vg-api-tokens.down.sql', 'utf8'));

module.exports = { up, down };
```

### Token Format

```
vg_tkn_<random_32_chars>_<checksum>

Example: vg_tkn_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6_q7r8
```

**Security Properties:**
- Prefix `vg_tkn_` identifies token type
- Random 32 chars = 160 bits entropy
- Stored as bcrypt hash (NEVER plaintext)
- Only shown ONCE during creation
- Revocable (server-side storage)

### Backend Implementation

**New File:** `server/lib/model/query/vg-api-tokens.js`
- `create(actorId, name, description, lifetimeDays, ...)` - Generate and store token
- `getByToken(plainToken)` - Authenticate token (bcrypt compare)
- `getByActorId(actorId)` - List user's tokens
- `revoke(tokenId, revokedBy)` - Revoke token
- `updateLastUsed(tokenId, ...)` - Track usage

**Modified:** `server/lib/http/preprocessors.js`
```javascript
// ADD: authByApiToken() function
// MODIFY: authHandler() to detect "vg_tkn_" prefix
// MODIFY: checkIpWhitelist() to skip for regular users with API tokens
```

**Modified:** `server/lib/resources/sessions.js`
```javascript
// MODIFY: createSession() to check user.isServiceAccount
// Apply 1-hour expiry for service accounts
```

### API Endpoints

**New File:** `server/lib/resources/vg-api-tokens.js`

**Route Pattern Consistency:**
- Follows existing web user pattern: `/v1/users/:id/*` (like `/v1/users/:id/totp/*`)
- **NOT** project-scoped (web users are system-wide, unlike app users)
- Auth: Web user session (self or admin)
- Permissions: User can manage own tokens, admin can manage any user's tokens

**Endpoints:**
```javascript
// List user's API tokens
service.get('/v1/users/:id/api-tokens', endpoint(({ VgApiTokens, Users }, { auth, params }) => ...))

// Create new API token (TOTP-protected if enabled)
service.post('/v1/users/:id/api-tokens', endpoint(({ VgApiTokens, Users, VgWebUserTotp }, { auth, params, body }) => ...))

// Revoke API token
service.delete('/v1/users/:id/api-tokens/:tokenId', endpoint(({ VgApiTokens, Users }, { auth, params }) => ...))

// Get token usage history
service.get('/v1/users/:id/api-tokens/:tokenId/usage', endpoint(({ VgApiTokens, Users }, { auth, params, queryOptions }) => ...))
```

**TOTP Protection:**
- Token creation requires TOTP verification if user has 2FA enabled
- Prevents attacker with stolen session from creating long-lived tokens

**VG Modularity:**
- ✅ New route file: `server/lib/resources/vg-api-tokens.js` (not editing core files)
- ✅ VG prefix: `vg_api_tokens` table, `VgApiTokens` model
- ✅ Follows existing VG pattern (like `vg-user-ip-whitelist.js`)
- ✅ No changes to app user routes (project-scoped, separate concern)

### Frontend UI

**New Component:** `client/src/components/user/edit/vg-api-tokens.vue`
- Token creation form (name, description, lifetime, TOTP code)
- Token display (shows full token ONCE with warning)
- Token list (active tokens with metadata)
- Revocation button
- Usage history view

---

## Part 2: Service Account System

### Database Schema

**Migration Files:** `server/lib/model/migrations/20260209-02-vg-service-accounts.{js,up.sql,down.sql}`

**File: 20260209-02-vg-service-accounts.up.sql**
```sql
-- VG: Service Account Flag
-- Add columns to users table to mark service accounts (automated systems)

BEGIN;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS is_service_account BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS service_account_marked_at TIMESTAMPTZ NULL;

-- Index for performance (partial index, only service accounts)
CREATE INDEX idx_users_service_account ON users (is_service_account)
  WHERE is_service_account = true;

COMMIT;
```

**File: 20260209-02-vg-service-accounts.down.sql**
```sql
-- VG: Rollback Service Account Flag

BEGIN;

DROP INDEX IF EXISTS idx_users_service_account;

ALTER TABLE users
  DROP COLUMN IF EXISTS is_service_account,
  DROP COLUMN IF EXISTS service_account_marked_at;

COMMIT;
```

**File: 20260209-02-vg-service-accounts.js**
```javascript
// VG: Service Account Flag
const up = (knex) => knex.raw(require('fs').readFileSync(__dirname + '/20260209-02-vg-service-accounts.up.sql', 'utf8'));
const down = (knex) => knex.raw(require('fs').readFileSync(__dirname + '/20260209-02-vg-service-accounts.down.sql', 'utf8'));

module.exports = { up, down };
```

### Backend Implementation

**Modified:** `server/lib/model/frames/user.js`
```javascript
class User extends Frame {
  get isServiceAccount() {
    return this.aux.data.isServiceAccount === true;
  }
}
```

**Modified:** `server/lib/model/query/users.js`
- Include `is_service_account` and `service_account_marked_at` in queries

**Modified:** `server/lib/http/preprocessors.js`
- `checkIpWhitelist()`: Enforce mandatory IP whitelist for service accounts
- Reject if service account has no IP whitelist entries

**Modified:** `server/lib/resources/sessions.js`
- Session lifetime: 1 hour for service accounts, 24 hours for regular users

### API Endpoints

**New File:** `server/lib/resources/vg-service-users.js`

**Route Pattern Consistency:**
- Follows web user pattern: `/v1/users/:id/service-account`
- System-wide scope (web users only)
- Auth: Admin only (requires `user.update` permission)
- **NOT** applicable to app users (separate actor type)

**Endpoints:**
```javascript
// Mark/unmark user as service account
service.patch('/v1/users/:id/service-account', endpoint(({ Users, Audits, VgUserIpWhitelist }, { auth, params, body }) => {
  // Validate IP whitelist exists before marking
  // Return 403 if no IP whitelist configured
  // Update users.is_service_account column
}))

// Get service account status (extend existing GET /v1/users/:id)
// Add fields to existing response:
// - isServiceAccount: boolean
// - serviceAccountMarkedAt: timestamp or null
```

**VG Modularity:**
- ✅ New route file: `server/lib/resources/vg-service-users.js`
- ✅ Extends existing GET /v1/users/:id (adds fields, doesn't replace)
- ✅ VG columns: `users.is_service_account`, `users.service_account_marked_at`
- ✅ Pattern: Like `vg-web-user-totp.js` (extends web users, not app users)

### Frontend UI

**New Component:** `client/src/components/user/edit/vg-service-account.vue`
- Checkbox to mark as service account
- Warning if no IP whitelist configured
- Explanation of service account features:
  - 1-hour sessions (not 24 hours)
  - Mandatory IP whitelist
  - Separate audit logging

---

## Part 3: Integration

### Authentication Flow Decision Tree

```
Bearer Token Received
  ↓
Does token start with "vg_tkn_"?
  ↓ YES → API Token Path
  │   ↓
  │   Lookup in vg_api_tokens (bcrypt compare)
  │   ↓ Valid?
  │   │   ↓
  │   │   Get user by actorId
  │   │   ↓
  │   │   Is user a service account?
  │   │   ↓ YES → Check IP whitelist (MANDATORY)
  │   │   ↓ NO  → Skip IP whitelist check
  │   │   ↓
  │   │   Allow request
  │
  ↓ NO → Session Token Path
      ↓
      Lookup in sessions table
      ↓ Valid?
      │   ↓
      │   Get user by actorId
      │   ↓
      │   Is user a service account?
      │   ↓ YES → Check IP whitelist (MANDATORY)
      │   ↓ NO  → Check IP whitelist (if configured)
      │   ↓
      │   Cookie auth? → Check TOTP
      │   Bearer auth? → Skip TOTP
      │   ↓
      │   Allow request
```

### Comparison Matrix

| Feature | Sessions | API Tokens |
|---------|----------|------------|
| **Creation** | POST /sessions (password) | POST /users/:id/api-tokens (TOTP UI) |
| **Lifetime (Regular)** | 24 hours | 30-365 days |
| **Lifetime (Service)** | 1 hour | 30-365 days |
| **TOTP Required** | At login | At creation |
| **IP Whitelist (Regular)** | Optional | NOT enforced |
| **IP Whitelist (Service)** | MANDATORY | MANDATORY |
| **Storage** | Cookies OR bearer | Bearer only |
| **Visibility** | Not shown in UI | Listed in UI |

---

## Part 4: Critical Files to Modify

### VG Modularity Pattern (Reference Existing VG Modules)

**Existing VG Modules (DO NOT MODIFY - Reference Only):**
```
server/lib/resources/vg-web-user-totp.js          ← Pattern for web user extensions
server/lib/resources/vg-user-ip-whitelist.js      ← Pattern for web user features
server/lib/resources/vg-app-user-auth.js          ← Pattern for app user features (separate!)
server/lib/model/query/vg-user-ip-whitelist.js    ← Pattern for VG query modules
server/lib/model/frames/vg-user-ip-whitelist.js   ← Pattern for VG frames
client/src/components/user/edit/vg-*.vue          ← Pattern for VG UI components
```

**This Plan Creates (Following VG Patterns):**
```
server/lib/resources/vg-api-tokens.js             ← NEW (follows vg-web-user-totp.js pattern)
server/lib/resources/vg-service-users.js          ← NEW (follows vg-user-ip-whitelist.js pattern)
server/lib/model/query/vg-api-tokens.js           ← NEW (follows vg-user-ip-whitelist.js query pattern)
server/lib/model/frames/vg-api-token.js           ← NEW (follows VG frame pattern)
client/src/components/user/edit/vg-api-tokens.vue ← NEW (follows existing vg-*.vue pattern)
client/src/components/user/edit/vg-service-account.vue ← NEW
```

---

### Backend Files (server/)

#### NEW VG Module Files (No Core Edits)

**Migration Pattern (Follow Existing VG Migrations):**
```
Existing VG migrations in server/lib/model/migrations/:
20260207-01-vg-security-features.js
20260207-01-vg-security-features.up.sql
20260207-01-vg-security-features.down.sql
20260208-01-vg-totp-enrollment-prompts.js
20260208-01-vg-totp-enrollment-prompts.up.sql
20260208-01-vg-totp-enrollment-prompts.down.sql
```

1. **lib/model/migrations/20260209-01-vg-api-tokens.js** (NEW)
   - Main migration file (references .up.sql and .down.sql)

2. **lib/model/migrations/20260209-01-vg-api-tokens.up.sql** (NEW)
   - Create `vg_api_tokens` table
   - Create `vg_api_token_usage` table
   - Create indexes

3. **lib/model/migrations/20260209-01-vg-api-tokens.down.sql** (NEW)
   - DROP tables and indexes

4. **lib/model/migrations/20260209-02-vg-service-accounts.js** (NEW)
   - Main migration file

5. **lib/model/migrations/20260209-02-vg-service-accounts.up.sql** (NEW)
   - ALTER `users` table: add `is_service_account`, `service_account_marked_at` columns
   - Create index on `is_service_account`

6. **lib/model/migrations/20260209-02-vg-service-accounts.down.sql** (NEW)
   - DROP columns from `users` table

**VG Migration Pattern:**
- ✅ Filename: `YYYYMMDD-NN-vg-feature-name.{js,up.sql,down.sql}`
- ✅ VG prefix in filename AND table names
- ✅ Three files per migration (main .js, .up.sql, .down.sql)
- ✅ Pattern reference: `20260207-01-vg-security-features.*`

3. **lib/model/query/vg-api-tokens.js** (NEW)
   - Token CRUD operations
   - Pattern reference: `lib/model/query/vg-user-ip-whitelist.js`

4. **lib/model/frames/vg-api-token.js** (NEW)
   - Token frame class
   - Pattern reference: `lib/model/frames/vg-user-ip-whitelist.js`

5. **lib/resources/vg-api-tokens.js** (NEW)
   - API endpoints: GET/POST/DELETE `/v1/users/:id/api-tokens`
   - Pattern reference: `lib/resources/vg-web-user-totp.js` (web user extensions)
   - **NOT** like `lib/resources/vg-app-user-auth.js` (different scope!)

6. **lib/resources/vg-service-users.js** (NEW)
   - API endpoint: PATCH `/v1/users/:id/service-account`
   - Pattern reference: `lib/resources/vg-user-ip-whitelist.js`

#### Core File Edits (Minimize & Document)

7. **lib/http/preprocessors.js** ⭐ CORE EDIT (MUST DOCUMENT)
   - Add `authByApiToken()` function (detect vg_tkn_ prefix)
   - Modify `authHandler()` to call authByApiToken()
   - Update `checkIpWhitelist()` for service account mandatory enforcement
   - **Document in:** `docs/vg/vg-server/vg_core_server_edits.md`

8. **lib/resources/sessions.js** ⭐ CORE EDIT (MUST DOCUMENT)
   - Modify session creation to check `user.isServiceAccount`
   - Apply 1-hour expiry for service accounts (vs 24 hours)
   - **Document in:** `docs/vg/vg-server/vg_core_server_edits.md`

9. **lib/model/frames/user.js** ⭐ CORE EDIT (MUST DOCUMENT)
   - Add `isServiceAccount` getter
   - Add `serviceAccountMarkedAt` getter
   - **Document in:** `docs/vg/vg-server/vg_core_server_edits.md`

10. **lib/model/query/users.js** ⭐ CORE EDIT (MUST DOCUMENT)
    - Include `is_service_account`, `service_account_marked_at` in SELECT queries
    - **Document in:** `docs/vg/vg-server/vg_core_server_edits.md`

---

### Frontend Files (client/)

#### NEW VG Component Files

11. **src/components/user/edit/vg-api-tokens.vue** (NEW)
    - Token creation form
    - Token list (active/revoked)
    - Usage history viewer
    - Pattern reference: `src/components/user/edit/vg-ip-whitelist.vue`

12. **src/components/user/edit/vg-service-account.vue** (NEW)
    - Service account toggle
    - IP whitelist requirement warning
    - Security feature explanation

13. **src/components/user/edit.vue** (CORE EDIT - ADD ROUTES)
    - Add routes to new VG components
    - Pattern: Follow existing VG component integration

---

### Documentation Files (NEW)

14. **docs/vg/vg-server/routes/vg-service-users.md** (NEW)
    - API documentation for:
      - POST /v1/users/:id/api-tokens
      - GET /v1/users/:id/api-tokens
      - DELETE /v1/users/:id/api-tokens/:tokenId
      - PATCH /v1/users/:id/service-account
    - Pattern reference: `docs/vg/vg-server/routes/web-user-totp.md`

15. **docs/vg/vg-server/vg_core_server_edits.md** (UPDATE)
    - Document ALL core file edits
    - Line numbers, reasons, diffs
    - Critical for rebase onto upstream

---

## Part 5: Testing Strategy

### Test Infrastructure (Existing Fixtures)

**Uses:**
- `testService` wrapper from `server/test/integration/setup`
- Jubilant temp database (auto-created per test)
- Pre-existing fixtures:
  - `alice@getodk.org` (password: `alice`) - Admin user
  - `chelsea@getodk.org` (password: `password4chelsea`) - Regular user
  - `bob@getodk.org` (password: `bob`) - Another user

**Pattern Reference:** `server/test/integration/api/vg-totp-enrollment.js`

**Key Patterns from TOTP Tests:**
1. **Container Access:**
   - Models: `container.VgApiTokens.methodName()`
   - Users: `container.Users.getByEmail('alice@getodk.org')`
   - DB queries: `container.run(sql`...`)` or `container.one(sql`...`)`

2. **Test Setup:**
   - Clear data: `DELETE FROM table WHERE ...`
   - Idempotent setup: `INSERT ... ON CONFLICT DO UPDATE`
   - Restore defaults: Update settings back after test

3. **Assertions:**
   - Booleans: `value.should.equal(true)`
   - Existence: `should.exist(value)` / `should.not.exist(value)`
   - Strings: `value.should.startWith('prefix')`
   - Time tolerance: `(diff < 10000).should.equal(true)`

4. **Login:**
   - Persistent: `const asAlice = await service.login('alice')`
   - Scoped: `service.login('alice', (asAlice) => ...)`
   - Inline user creation: Create user within callback

### Integration Tests (Write Tests FIRST - TDD)

**File:** `server/test/integration/api/vg-api-tokens.js` (NEW)

```javascript
const should = require('should');
const { sql } = require('slonik');
require('../assertions');
const { testService } = require('../setup');

describe('api: vg API tokens', () => {

  describe('POST /v1/users/:id/api-tokens - creation', () => {

    it('should create API token with valid name', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const userId = alice.get().id;

      const response = await asAlice.post(`/v1/users/${userId}/api-tokens`)
        .send({
          name: 'Test Token',
          description: 'Integration test',
          lifetimeDays: 90
        })
        .expect(201);

      response.body.fullToken.should.startWith('vg_tkn_');
      response.body.tokenPrefix.should.be.a.String();
      response.body.name.should.equal('Test Token');
    }));

    it('should reject missing name parameter', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');

      await asAlice.post(`/v1/users/${alice.get().id}/api-tokens`)
        .send({ lifetimeDays: 90 })
        .expect(400); // missingParameters
    }));

    it('should require TOTP verification if user has 2FA enabled', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const userId = alice.get().id;
      const actorId = alice.get().actor.id;

      // Enable TOTP for Alice
      await container.run(sql`
        INSERT INTO vg_web_user_totp ("actorId", totp_secret, totp_enabled, totp_enabled_at, created_at, updated_at)
        VALUES (${actorId}, 'JBSWY3DPEHPK3PXP', true, NOW(), NOW(), NOW())
        ON CONFLICT ("actorId") DO UPDATE
        SET totp_enabled = true, totp_enabled_at = NOW()
      `);

      // Should reject without TOTP token
      await asAlice.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'Test', lifetimeDays: 90 })
        .expect(400); // Missing totpToken

      // Clean up
      await container.run(sql`
        DELETE FROM vg_web_user_totp WHERE "actorId" = ${actorId}
      `);
    }));

    it('should reject invalid lifetime days', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');

      await asAlice.post(`/v1/users/${alice.get().id}/api-tokens`)
        .send({ name: 'Test', lifetimeDays: 9999 }) // > 365
        .expect(400); // invalidDataTypeOfParameter
    }));
  });

  describe('POST /v1/users/:id/api-tokens - authentication', () => {

    it('should authenticate API requests with valid token', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const userId = alice.get().id;

      // Create token
      const tokenResponse = await asAlice.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'API Test Token', lifetimeDays: 90 })
        .expect(201);

      const token = tokenResponse.body.fullToken;

      // Use token for API call
      await service.get('/v1/projects')
        .set('Authorization', `Bearer ${token}`)
        .expect(200);
    }));

    it('should reject expired token', testService(async (service, container) => {
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const actorId = alice.get().actor.id;

      // Create expired token directly in DB
      await container.run(sql`
        INSERT INTO vg_api_tokens ("actorId", token, token_prefix, name, created_at, expires_at)
        VALUES (
          ${actorId},
          '$2b$04$abcdefghijklmnopqrstuv',  -- Dummy hash
          'vg_tkn_expired',
          'Expired Test',
          NOW() - INTERVAL '2 days',
          NOW() - INTERVAL '1 day'
        )
      `);

      // Should reject
      await service.get('/v1/projects')
        .set('Authorization', 'Bearer vg_tkn_expired_dummy')
        .expect(401);

      // Clean up
      await container.run(sql`
        DELETE FROM vg_api_tokens WHERE token_prefix = 'vg_tkn_expired'
      `);
    }));

    it('should reject revoked token', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const userId = alice.get().id;

      // Create token
      const tokenResponse = await asAlice.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'To Be Revoked', lifetimeDays: 90 })
        .expect(201);

      const tokenId = tokenResponse.body.id;
      const fullToken = tokenResponse.body.fullToken;

      // Verify it works first
      await service.get('/v1/projects')
        .set('Authorization', `Bearer ${fullToken}`)
        .expect(200);

      // Revoke it
      await asAlice.delete(`/v1/users/${userId}/api-tokens/${tokenId}`)
        .expect(200);

      // Should no longer work
      await service.get('/v1/projects')
        .set('Authorization', `Bearer ${fullToken}`)
        .expect(401);
    }));
  });

  describe('GET /v1/users/:id/api-tokens - listing', () => {

    it('should list user API tokens', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const userId = alice.get().id;
      const actorId = alice.get().actor.id;

      // Clean up existing tokens
      await container.run(sql`
        DELETE FROM vg_api_tokens WHERE "actorId" = ${actorId}
      `);

      // Create test token
      await asAlice.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'List Test Token', lifetimeDays: 90 })
        .expect(201);

      // List tokens
      const response = await asAlice.get(`/v1/users/${userId}/api-tokens`)
        .expect(200);

      response.body.should.be.an.Array();
      response.body.length.should.equal(1);
      response.body[0].name.should.equal('List Test Token');
      should.not.exist(response.body[0].fullToken); // Full token never returned in list
    }));

    it('should not show full token in listing', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const userId = alice.get().id;

      await asAlice.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'Security Test', lifetimeDays: 90 })
        .expect(201);

      const response = await asAlice.get(`/v1/users/${userId}/api-tokens`)
        .expect(200);

      response.body.forEach(token => {
        should.not.exist(token.fullToken);
        should.exist(token.tokenPrefix); // Only prefix shown
      });
    }));
  });

  describe('DELETE /v1/users/:id/api-tokens/:tokenId - revocation', () => {

    it('should revoke token', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const userId = alice.get().id;

      const tokenResponse = await asAlice.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'Revoke Test', lifetimeDays: 90 })
        .expect(201);

      await asAlice.delete(`/v1/users/${userId}/api-tokens/${tokenResponse.body.id}`)
        .expect(200);

      // Verify revocation in DB
      const revoked = await container.one(sql`
        SELECT revoked_at FROM vg_api_tokens WHERE id = ${tokenResponse.body.id}
      `);

      should.exist(revoked.revoked_at);
    }));

    it('should prevent non-owner from revoking token', testService(async (service, container) => {
      // Create token as Alice
      const asAlice = await service.login('alice');
      const alice = await container.Users.getByEmail('alice@getodk.org');
      const userId = alice.get().id;

      const tokenResponse = await asAlice.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'Owner Test', lifetimeDays: 90 })
        .expect(201);

      // Create another user (Chelsea) and try to revoke Alice's token
      const asChelsea = await service.login('chelsea');
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');

      await asChelsea.delete(`/v1/users/${userId}/api-tokens/${tokenResponse.body.id}`)
        .expect(403); // Insufficient rights
    }));
  });
});
```

**File:** `server/test/integration/api/vg-service-accounts.js` (NEW)

```javascript
const should = require('should');
const { sql } = require('slonik');
require('../assertions');
const { testService } = require('../setup');

describe('api: vg service accounts', () => {

  describe('PATCH /v1/users/:id/service-account - marking', () => {

    it('should reject marking as service account without IP whitelist', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');
      const userId = chelsea.get().id;
      const actorId = chelsea.get().actor.id;

      // Ensure Chelsea has no IP whitelist
      await container.run(sql`
        DELETE FROM vg_user_ip_whitelist WHERE "actorId" = ${actorId}
      `);

      // Should reject
      await asAlice.patch(`/v1/users/${userId}/service-account`)
        .send({ isServiceAccount: true })
        .expect(403); // IP whitelist required
    }));

    it('should mark as service account when IP whitelist exists', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');
      const userId = chelsea.get().id;
      const actorId = chelsea.get().actor.id;

      // Add IP whitelist entry
      await container.run(sql`
        INSERT INTO vg_user_ip_whitelist ("actorId", ip_cidr, description, enabled)
        VALUES (${actorId}, '192.168.1.0/24'::cidr, 'Test network', true)
        ON CONFLICT DO NOTHING
      `);

      // Should succeed
      await asAlice.patch(`/v1/users/${userId}/service-account`)
        .send({ isServiceAccount: true })
        .expect(200);

      // Verify in DB
      const user = await container.one(sql`
        SELECT is_service_account FROM users WHERE "actorId" = ${actorId}
      `);

      user.is_service_account.should.equal(true);

      // Clean up
      await container.run(sql`
        UPDATE users SET is_service_account = false WHERE "actorId" = ${actorId}
      `);
      await container.run(sql`
        DELETE FROM vg_user_ip_whitelist WHERE "actorId" = ${actorId}
      `);
    }));

    it('should unmark service account', testService(async (service, container) => {
      const asAlice = await service.login('alice');
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');
      const userId = chelsea.get().id;
      const actorId = chelsea.get().actor.id;

      // Set up as service account
      await container.run(sql`
        UPDATE users SET is_service_account = true WHERE "actorId" = ${actorId}
      `);

      // Unmark
      await asAlice.patch(`/v1/users/${userId}/service-account`)
        .send({ isServiceAccount: false })
        .expect(200);

      // Verify
      const user = await container.one(sql`
        SELECT is_service_account FROM users WHERE "actorId" = ${actorId}
      `);

      user.is_service_account.should.equal(false);
    }));
  });

  describe('session lifetime for service accounts', () => {

    it('should create 1-hour sessions for service accounts', testService(async (service, container) => {
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');
      const actorId = chelsea.get().actor.id;

      // Set up as service account
      await container.run(sql`
        UPDATE users SET is_service_account = true WHERE "actorId" = ${actorId}
      `);

      // Add IP whitelist
      await container.run(sql`
        INSERT INTO vg_user_ip_whitelist ("actorId", ip_cidr, enabled)
        VALUES (${actorId}, '127.0.0.1'::cidr, true)
        ON CONFLICT DO NOTHING
      `);

      // Login
      const response = await service.post('/v1/sessions')
        .set('X-Forwarded-For', '127.0.0.1')
        .send({ email: 'chelsea@getodk.org', password: 'password4chelsea' })
        .expect(200);

      const expiresAt = new Date(response.body.expiresAt);
      const createdAt = new Date(response.body.createdAt);
      const diffHours = (expiresAt - createdAt) / (1000 * 60 * 60);

      // Should be approximately 1 hour (not 24)
      diffHours.should.be.approximately(1, 0.1);

      // Clean up
      await container.run(sql`
        UPDATE users SET is_service_account = false WHERE "actorId" = ${actorId}
      `);
      await container.run(sql`
        DELETE FROM vg_user_ip_whitelist WHERE "actorId" = ${actorId}
      `);
    }));

    it('should create 24-hour sessions for regular users', testService(async (service, container) => {
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');
      const actorId = chelsea.get().actor.id;

      // Ensure NOT service account
      await container.run(sql`
        UPDATE users SET is_service_account = false WHERE "actorId" = ${actorId}
      `);

      // Login
      const response = await service.post('/v1/sessions')
        .send({ email: 'chelsea@getodk.org', password: 'password4chelsea' })
        .expect(200);

      const expiresAt = new Date(response.body.expiresAt);
      const createdAt = new Date(response.body.createdAt);
      const diffHours = (expiresAt - createdAt) / (1000 * 60 * 60);

      // Should be approximately 24 hours
      diffHours.should.be.approximately(24, 1);
    }));
  });

  describe('IP whitelist enforcement for service accounts', () => {

    it('should enforce IP whitelist for service account sessions', testService(async (service, container) => {
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');
      const actorId = chelsea.get().actor.id;

      // Set up as service account with IP whitelist
      await container.run(sql`
        UPDATE users SET is_service_account = true WHERE "actorId" = ${actorId}
      `);
      await container.run(sql`
        INSERT INTO vg_user_ip_whitelist ("actorId", ip_cidr, enabled)
        VALUES (${actorId}, '192.168.1.0/24'::cidr, true)
        ON CONFLICT DO NOTHING
      `);

      // Login and get session token
      const loginResponse = await service.post('/v1/sessions')
        .set('X-Forwarded-For', '192.168.1.100')
        .send({ email: 'chelsea@getodk.org', password: 'password4chelsea' })
        .expect(200);

      const token = loginResponse.body.token;

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

      // Clean up
      await container.run(sql`
        UPDATE users SET is_service_account = false WHERE "actorId" = ${actorId}
      `);
      await container.run(sql`
        DELETE FROM vg_user_ip_whitelist WHERE "actorId" = ${actorId}
      `);
    }));

    it('should enforce IP whitelist for service account API tokens', testService(async (service, container) => {
      const asChelsea = await service.login('chelsea');
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');
      const userId = chelsea.get().id;
      const actorId = chelsea.get().actor.id;

      // Set up as service account with IP whitelist
      await container.run(sql`
        UPDATE users SET is_service_account = true WHERE "actorId" = ${actorId}
      `);
      await container.run(sql`
        INSERT INTO vg_user_ip_whitelist ("actorId", ip_cidr, enabled)
        VALUES (${actorId}, '192.168.1.0/24'::cidr, true)
        ON CONFLICT DO NOTHING
      `);

      // Create API token
      const tokenResponse = await asChelsea.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'Service Account Token', lifetimeDays: 90 })
        .expect(201);

      const apiToken = tokenResponse.body.fullToken;

      // From whitelisted IP - should work
      await service.get('/v1/projects')
        .set('Authorization', `Bearer ${apiToken}`)
        .set('X-Forwarded-For', '192.168.1.100')
        .expect(200);

      // From non-whitelisted IP - should fail
      await service.get('/v1/projects')
        .set('Authorization', `Bearer ${apiToken}`)
        .set('X-Forwarded-For', '10.0.0.1')
        .expect(403);

      // Clean up
      await container.run(sql`
        DELETE FROM vg_api_tokens WHERE "actorId" = ${actorId}
      `);
      await container.run(sql`
        UPDATE users SET is_service_account = false WHERE "actorId" = ${actorId}
      `);
      await container.run(sql`
        DELETE FROM vg_user_ip_whitelist WHERE "actorId" = ${actorId}
      `);
    }));

    it('should NOT enforce IP whitelist for regular user API tokens', testService(async (service, container) => {
      const asChelsea = await service.login('chelsea');
      const chelsea = await container.Users.getByEmail('chelsea@getodk.org');
      const userId = chelsea.get().id;
      const actorId = chelsea.get().actor.id;

      // Ensure NOT service account
      await container.run(sql`
        UPDATE users SET is_service_account = false WHERE "actorId" = ${actorId}
      `);

      // Create API token
      const tokenResponse = await asChelsea.post(`/v1/users/${userId}/api-tokens`)
        .send({ name: 'Regular User Token', lifetimeDays: 90 })
        .expect(201);

      const apiToken = tokenResponse.body.fullToken;

      // Should work from ANY IP (no whitelist enforcement)
      await service.get('/v1/projects')
        .set('Authorization', `Bearer ${apiToken}`)
        .set('X-Forwarded-For', '203.0.113.50')
        .expect(200);

      await service.get('/v1/projects')
        .set('Authorization', `Bearer ${apiToken}`)
        .set('X-Forwarded-For', '198.51.100.1')
        .expect(200);

      // Clean up
      await container.run(sql`
        DELETE FROM vg_api_tokens WHERE "actorId" = ${actorId}
      `);
    }));
  });
});
```

### Test Workflow (TDD)

**Step 1:** Write test (RED)
```bash
docker compose exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-api-tokens.js'
# Test fails - endpoint doesn't exist yet
```

**Step 2:** Implement minimum code (GREEN)
```bash
# Add route, implement just enough to pass
# Re-run test → passes
```

**Step 3:** Refactor
```bash
# Improve code quality, tests still pass
```

**Step 4:** Document
```bash
# Update docs/vg/vg-server/routes/vg-service-users.md with confirmed API behavior
```

---

## Part 6: VG Modularity & Implementation Workflow

### VG Modularity Principles

**NEW Files (Preferred):**
- `server/lib/model/query/vg-api-tokens.js` - Token CRUD operations
- `server/lib/model/frames/vg-api-token.js` - Token frame
- `server/lib/resources/vg-api-tokens.js` - API endpoints for tokens
- `server/lib/resources/vg-service-users.js` - Service account endpoints
- `client/src/components/user/edit/vg-api-tokens.vue` - Token management UI
- `client/src/components/user/edit/vg-service-account.vue` - Service account UI

**CORE Edits (Minimize & Document):**
- `server/lib/http/preprocessors.js` - Add API token detection, service account IP check
- `server/lib/model/frames/user.js` - Add `isServiceAccount` getter
- `server/lib/model/query/users.js` - Include service account fields
- `server/lib/resources/sessions.js` - Service account session lifetime

**Documentation of Core Edits:**
- ALL core file edits MUST be documented in `docs/vg/vg-server/vg_core_server_edits.md`
- Format: File path, line numbers, reason, diff summary

### Implementation Phasing

**PHASE 1: Backend API (TDD)**
1. Design API contract (routes, request/response schemas)
2. Create beads issues for each endpoint
3. Write integration tests FIRST (RED)
4. Implement backend to pass tests (GREEN)
5. Document routes in `docs/vg/vg-server/routes/vg-service-users.md`
6. Document core edits in `docs/vg/vg-server/vg_core_server_edits.md`

**PHASE 2: Frontend UI**
1. Create beads issues for UI components
2. Build components against confirmed API
3. Write E2E tests
4. User documentation

### API-First TDD Workflow

**Step 1: Design API Contract**
```markdown
## POST /v1/users/:id/api-tokens

**Request:**
{
  "name": "My Jupyter Notebook",
  "description": "Data analysis scripts",
  "lifetimeDays": 90,
  "totpToken": "123456"
}

**Response (201):**
{
  "id": 123,
  "fullToken": "vg_tkn_...",
  "tokenPrefix": "vg_tkn_abc...",
  "expiresAt": "2026-05-10T...",
  "warning": "This is the only time..."
}

**Errors:**
- 400: Missing name, invalid lifetimeDays
- 401: Invalid TOTP code
- 403: Insufficient permissions
```

**Step 2: Write Integration Test (RED)**
```javascript
it('should create API token with TOTP verification', testService(async (service, container) => {
  // Test implementation BEFORE backend exists
  const response = await service.post('/v1/users/1/api-tokens')
    .send({ name: 'Test', lifetimeDays: 90, totpToken: '123456' })
    .expect(201);

  response.body.fullToken.should.startWith('vg_tkn_');
}));
```

**Step 3: Implement Backend (GREEN)**
```javascript
// Implement just enough to pass the test
service.post('/v1/users/:id/api-tokens', endpoint(...));
```

**Step 4: Document in routes/vg-service-users.md**
- Confirm API behavior via passing tests
- Document request/response schemas
- Document error codes
- Add examples

### Beads Issues Structure

**Epic: API Token Management**
- `beads-xxx`: Design API contract
- `beads-xxx`: Create vg_api_tokens migration
- `beads-xxx`: Implement VgApiTokens query module (TDD)
- `beads-xxx`: Implement POST /v1/users/:id/api-tokens endpoint (TDD)
- `beads-xxx`: Implement GET /v1/users/:id/api-tokens endpoint (TDD)
- `beads-xxx`: Implement DELETE /v1/users/:id/api-tokens/:tokenId endpoint (TDD)
- `beads-xxx`: Update preprocessors.js for API token auth (TDD)
- `beads-xxx`: Document routes in vg-service-users.md
- `beads-xxx`: Document core edits in vg_core_server_edits.md

**Epic: Service Account System**
- `beads-xxx`: Create service account migration
- `beads-xxx`: Add isServiceAccount to User frame
- `beads-xxx`: Implement PATCH /v1/users/:id/service-account endpoint (TDD)
- `beads-xxx`: Update sessions.js for service account lifetime (TDD)
- `beads-xxx`: Update preprocessors.js for mandatory IP whitelist (TDD)
- `beads-xxx`: Document routes in vg-service-users.md
- `beads-xxx`: Document core edits in vg_core_server_edits.md

**Epic: Frontend UI (After Backend Complete)**
- `beads-xxx`: Build vg-api-tokens.vue component
- `beads-xxx`: Build vg-service-account.vue component
- `beads-xxx`: Write E2E tests
- `beads-xxx`: User documentation

### Backward Compatibility

**No Breaking Changes:**
- App user authentication unchanged (MEDRES-ODK-Collect compatible)
- OpenRosa protocol unchanged
- Field key authentication unchanged
- Web user sessions continue working
- Users not marked as service accounts see no behavior change

---

## Part 7: Documentation Requirements

### CRITICAL: Core Edits Documentation
**File:** `docs/vg/vg-server/vg_core_server_edits.md`

MUST document ALL modifications to upstream core files:
```markdown
## lib/http/preprocessors.js

**Lines Modified:** 45-67, 99-109

**Reason:** Add API token authentication, service account IP whitelist enforcement

**Changes:**
- Added authByApiToken() function (lines 45-67)
- Modified authHandler() to detect vg_tkn_ prefix (line 102)
- Updated checkIpWhitelist() to enforce for service accounts (lines 150-165)

**VG Pattern:** Minimal core edit - only auth detection logic. Token validation in vg-api-tokens.js
```

### API Documentation (Updated During TDD)
**File:** `docs/vg/vg-server/routes/vg-service-users.md`

Document as tests pass:
- Request/response schemas (confirmed via tests)
- Error codes (confirmed via tests)
- Examples (from test cases)
- Authentication requirements

### Admin Guides (After Implementation)
- `docs/vg/vg-server/api-token-management.md` - How to create/use API tokens
- `docs/vg/vg-server/service-accounts-guide.md` - When and how to use service accounts

### Developer Documentation
- `docs/vg/vg-server/authentication-flows.md` - Updated auth flow diagrams

---

## Critical Decisions Made

1. **API Token Lifetime:** 90 days default (30-365 day range)
2. **Token Format:** `vg_tkn_<random>_<checksum>` (not JWT - must be revocable)
3. **Token Storage:** bcrypt hash (same as passwords)
4. **Token Scope:** Same permissions as user account (no per-token scoping yet)
5. **IP Whitelist Enforcement:**
   - Regular users + API tokens: NOT enforced (allows travel)
   - Service accounts + any auth: ENFORCED (static infrastructure)
6. **TOTP for Token Creation:** Required if user has 2FA enabled
7. **Service Account Session Lifetime:** 1 hour (vs 24 hours)

---

## Success Metrics

**Security:**
- 100% of service accounts have IP whitelist configured
- Service account sessions limited to 1 hour
- Clear audit trail (serviceAccount flag, token usage tracking)

**Usability:**
- Researchers can create API tokens via UI (no pyodk code changes needed initially)
- pyodk compatibility maintained (username/password flow works)
- Future: pyodk supports pre-created tokens (separate project)

**Adoption:**
- Admins mark known service accounts
- Human users create API tokens for Jupyter notebooks
- Documentation clear and complete

---

## Future Enhancements (Out of Scope)

1. **pyodk Token Support** (separate project)
   - Add `token` parameter to pyodk Client config
   - Users paste token from UI into `.pyodk_config.toml`

2. **Per-Token Scoping**
   - Allow tokens with subset of user's permissions
   - Useful for minimal-privilege automation

3. **API Key System** (alternative to tokens)
   - Separate from sessions (different table)
   - Rotating keys
   - Key usage dashboard

---

## Verification Plan

### Phase 1: Backend API Verification

**Test via Integration Tests:**
```bash
# API token creation
docker compose exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-api-tokens.js'

# Service account endpoints
docker compose exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-service-accounts.js'
```

**Manual API Testing (curl):**
```bash
# 1. Create API token (with TOTP)
curl -X POST https://central.local/v1/users/1/api-tokens \
  -H "Cookie: __Host-session=..." \
  -d '{"name":"Test","lifetimeDays":90,"totpToken":"123456"}'

# 2. Use API token
curl -X GET https://central.local/v1/projects \
  -H "Authorization: Bearer vg_tkn_..."

# 3. Mark as service account
curl -X PATCH https://central.local/v1/users/2/service-account \
  -H "Cookie: __Host-session=..." \
  -d '{"isServiceAccount":true}'
```

### Phase 2: Compatibility Verification

**CRITICAL: Verify App Users Unchanged**
```bash
# App user login (MUST work unchanged)
curl -X POST https://central.local/v1/projects/1/app-users/login \
  -d '{"username":"appuser","password":"pass"}'

# Should return token as before (no changes)
```

**CRITICAL: Verify OpenRosa Unchanged**
```bash
# Form list (MUST work unchanged)
curl -X GET https://central.local/formList \
  -H "Authorization: Bearer <field-key-token>"

# Submission (MUST work unchanged)
curl -X POST https://central.local/submission \
  -H "Authorization: Bearer <field-key-token>" \
  -F xml_submission_file=@submission.xml
```

**Verify Web User Sessions Still Work**
```bash
# Login (should still work)
curl -X POST https://central.local/v1/sessions \
  -d '{"email":"user@example.com","password":"pass"}'

# Use session token (should still work)
curl -X GET https://central.local/v1/projects \
  -H "Authorization: Bearer <session-token>"
```

### Phase 3: Service Account Verification

**Test IP Whitelist Enforcement:**
```bash
# Service account WITHOUT IP whitelist → should reject
curl -X PATCH .../service-account -d '{"isServiceAccount":true}'
# Expected: 403 "IP whitelist must be configured"

# Service account WITH IP whitelist → should accept
curl -X POST .../ip-whitelist -d '{"ipAddress":"192.168.1.0/24"}'
curl -X PATCH .../service-account -d '{"isServiceAccount":true}'
# Expected: 200 OK

# Service account access from non-whitelisted IP → should reject
curl -X GET .../projects -H "Authorization: Bearer ..." -H "X-Forwarded-For: 10.0.0.1"
# Expected: 403 "IP not whitelisted"
```

**Test Session Lifetime:**
```bash
# Regular user session
# Expected expiresAt: now + 24 hours

# Service account session
# Expected expiresAt: now + 1 hour
```

### Phase 4: Frontend UI Verification

**Manual Testing:**
1. Log into web UI as admin
2. Navigate to user edit page
3. Verify "API Tokens" tab appears
4. Create token (enter TOTP code)
5. Verify token shown once with warning
6. Verify token list shows created tokens
7. Revoke token
8. Verify token no longer works

9. Navigate to "Service Account" section
10. Try to enable without IP whitelist → should show warning
11. Add IP whitelist entry
12. Enable service account → should succeed
13. Verify 1-hour session lifetime in login

## References

- **Existing Plan:** `plan/service-account-security.md` (incorporated + enhanced)
- **IP Whitelist:** `docs/vg/vg-server/vg_ip_whitelist_admin_guide.md`
- **Auth Docs:** `docs/vg/web-vs-upstream-app-user-vs-vg-app-user-auth.md`
- **Core Edits Doc:** `docs/vg/vg-server/vg_core_server_edits.md`
