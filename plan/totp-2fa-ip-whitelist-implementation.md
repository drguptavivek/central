# TOTP 2FA + IP Whitelist Implementation Plan

**Session Date:** 2026-02-07
**Feature:** Two-Factor Authentication (TOTP) + Per-User IP Whitelist for ODK Central

## Overview

Implementing two orthogonal security features:
1. **TOTP 2FA** - Mandatory for web users (cookie-based auth)
2. **Per-user IP Whitelist** - For API users (Bearer token auth)

Key design: Same user can be both web user (with 2FA) AND API user (with IP whitelist).

---

## Progress Summary

### ✅ Completed

#### 1. Database Migration (Task #1)
- ✅ Created tables in `server/docs/sql/vg_app_user_auth.sql`:
  - `vg_web_user_totp` - TOTP secrets (encrypted)
  - `vg_web_user_totp_backup_codes` - Backup codes (bcrypt hashed)
  - `vg_web_user_totp_attempts` - Rate limiting tracking
  - `vg_user_ip_whitelist` - IP whitelist entries (CIDR support)
- ✅ Added `totp_verified` column to `sessions` table
- ✅ Added vg_settings for 2FA configuration:
  - `vg_web_user_totp_mandatory` (default: false)
  - `vg_totp_max_failures` (default: 5)
  - `vg_totp_window_minutes` (default: 5)
  - `vg_totp_lock_duration_minutes` (default: 15)
- ✅ Applied migration to production and test databases

**Files Modified:**
- `server/docs/sql/vg_app_user_auth.sql`

#### 2. TOTP Utilities (Task #2)
- ✅ Installed dependencies: `speakeasy`, `qrcode`
- ✅ Created `server/lib/util/vg-totp.js` with:
  - Secret generation (base32, 256-bit)
  - QR code generation (data URL)
  - Token verification (with time window)
  - Backup code generation (8-digit codes)
  - AES-256-CBC encryption/decryption for secrets

**Files Created:**
- `server/lib/util/vg-totp.js`

**Known Issues:**
- Minor: Unused import `promisify` in vg-totp.js (line 9)
- Minor: TSLint suggests ES module conversion (not critical for this codebase)

### 🚧 In Progress (Interrupted by User)

#### Task #3: Backend TOTP Query Modules (RESUMED)
**Status:** Previously interrupted, but files were already complete

**What Was Being Implemented:**
- Domain logic file: `server/lib/domain/vg-web-user-totp.js` ✅
- Query module: `server/lib/model/query/vg-web-user-totp.js` ✅
- Query module: `server/lib/model/query/vg-user-ip-whitelist.js` ✅
- Resource endpoints: `server/lib/resources/vg-web-user-totp.js` ✅
- Resource endpoints: `server/lib/resources/vg-user-ip-whitelist.js` ✅
- Core modifications: `server/lib/http/preprocessors.js` ✅
- Core modifications: `server/lib/resources/sessions.js` ✅

#### 3. Backend TOTP Query Modules (Task #3) - ✅ COMPLETED
- ✅ Created `server/lib/model/query/vg-web-user-totp.js`
- ✅ Created `server/lib/model/query/vg-user-ip-whitelist.js`
- ✅ Database operations for TOTP setup, verification, backup codes
- ✅ Database operations for IP whitelist CRUD and checking

#### 4. TOTP Resource Endpoints (Task #4) - ✅ COMPLETED
- ✅ Created `server/lib/resources/vg-web-user-totp.js`
- ✅ Endpoints: setup, enable, disable, backup-codes/regenerate, totp-verify
- ✅ Authorization checks and audit logging
- ✅ Registered in `server/lib/http/service.js` (line 102)

#### 5. IP Whitelist Resource Endpoints (Task #5) - ✅ COMPLETED
- ✅ Created `server/lib/resources/vg-user-ip-whitelist.js`
- ✅ Endpoints: GET, POST, PATCH, DELETE for IP whitelist entries
- ✅ CIDR validation
- ✅ Registered in `server/lib/http/service.js` (line 103)

#### 6. Preprocessors.js Modifications (Task #6) - ✅ COMPLETED
- ✅ Added `getClientIp()` utility (X-Forwarded-For handling)
- ✅ Cookie auth: TOTP verification check after session validation
- ✅ Bearer auth: IP whitelist check after token validation
- ✅ Added Problem definitions: `totpRequired`, `ipNotWhitelisted`

#### 7. Sessions Endpoint Modifications (Task #7) - ✅ COMPLETED
- ✅ Two-phase login flow implemented
- ✅ Check if user has 2FA enabled after password verification
- ✅ Create session with `totpVerified=false` when TOTP enabled
- ✅ Return `{ requireTotp: true }` to trigger frontend 2FA step

#### Domain Logic - ✅ COMPLETED
- ✅ Created `server/lib/domain/vg-web-user-totp.js`
- ✅ Business logic for TOTP setup, enable, disable
- ✅ Backup code generation and verification
- ✅ Rate limiting (5 failures in 5 min = 15 min lockout)

#### Resources Registration - ✅ COMPLETED
- ✅ Registered in `server/lib/http/service.js`

---

## Remaining Tasks

### Backend Implementation

**All core backend tasks are complete!** ✅

#### Testing

- ✅ **Task #8:** Write backend unit tests for TOTP utilities - **COMPLETED**
  - Test file: `test/unit/util/vg-totp.js`
  - ✅ Test TOTP generation, verification, encryption
  - ✅ Test backup code generation
  - ✅ 25 tests passing

- 🚧 **Task #9:** Write backend integration tests for TOTP flow - **IN PROGRESS - NEW BLOCKER**
  - Test file: `test/integration/api/vg-web-user-totp.js` - ✅ CREATED
  - Test fixture: `test/integration/fixtures/04-vg-web-user-totp.js` - ✅ CREATED
  - **PREVIOUS BLOCKER RESOLVED:** Fixed test framework cleanup in `server/test/integration/setup.js`
    - Added superuser connection to drop all objects (tables, sequences, enums)
    - Fixed SQL query for enum types (joined with pg_namespace)
  - **NEW BLOCKER:** Service migrations fail with "function hash_text already exists"
    - Root cause: citext extension provides `hash_text` function, migrations try to create it
    - Service enters restart loop, cannot start successfully
    - Affects main `odk` database, preventing all testing
  - **Workaround Options:**
    1. Modify migration file to use `CREATE OR REPLACE FUNCTION` (upstream change, not ideal)
    2. Drop citext extension before migrations, recreate after (complex)
    3. Pre-create migration record to skip problematic migration
    4. Use fresh database without citext initially
  - **Status:** Integration test code is complete and ready to run once environment is fixed
  - Test file: `test/integration/api/vg-web-user-totp.js`
  - Full 2FA setup flow (setup → enable → login)
  - TOTP verification during login
  - Backup code usage and marking as used
  - Rate limiting (5 failures → lockout)
  - Disable flow with password verification

- [ ] **Task #10:** Write backend integration tests for IP whitelist
  - Test file: `test/integration/api/vg-user-ip-whitelist.js`
  - IP whitelist CRUD operations
  - Bearer token enforcement (allowed vs blocked IPs)
  - CIDR range matching
  - Audit logging for violations
  - Cookie auth unaffected by IP whitelist
  - Bearer auth unaffected by TOTP requirement

### Frontend Implementation

#### Components

- [ ] **Task #11:** Modify frontend login component for two-phase flow
  - **CRITICAL CORE FILE EDIT**
  - Modify `client/src/components/account/login.vue`
  - Add second phase for TOTP verification when `{ requireTotp: true }`
  - Show 6-digit code input field
  - Add "Use backup code instead" toggle
  - Call POST /v1/sessions/totp-verify with code
  - **Document in:** `docs/vg/vg-client/vg_core_client_edits.md`

- [ ] **Task #12:** Create frontend TOTP settings component
  - Create `client/src/components/user/edit/vg-totp-settings.vue`
  - Display current 2FA status (enabled/disabled)
  - "Enable 2FA" button → trigger setup modal
  - "Disable 2FA" button → password confirmation dialog
  - "Regenerate backup codes" button
  - Show last enabled date

- [ ] **Task #13:** Create frontend TOTP setup modal
  - Create `client/src/components/vg/vg-totp-setup-modal.vue`
  - Step 1: Display QR code from setup endpoint
  - Step 2: User enters first TOTP code to verify
  - Step 3: Display backup codes with download button
  - Step 4: Confirm backup codes saved (checkbox)

- [ ] **Task #14:** Create frontend IP whitelist component
  - Create `client/src/components/user/edit/vg-ip-whitelist.vue`
  - Display list of IP whitelist entries
  - Add entry form (IP/CIDR input with validation)
  - Edit/delete entries
  - Show warnings for CIDR ranges

#### Testing

- [ ] **Task #15:** Write frontend E2E tests for 2FA flow
  - Test file: `client/test/e2e/vg-totp.spec.js`
  - Setup wizard complete flow
  - Login with TOTP code
  - Login with backup code
  - Rate limiting lockout

- [ ] **Task #16:** Write frontend E2E tests for IP whitelist
  - Test file: `client/test/e2e/vg-ip-whitelist.spec.js`
  - Add/edit/delete IP whitelist entries
  - CIDR validation
  - UI warnings for wide ranges

### Documentation

- [ ] **Task #17:** Write documentation for 2FA
  - `docs/vg/vg-server/vg_2fa_admin_guide.md` - Admin guide
  - `docs/vg/vg-client/vg_2fa_user_guide.md` - User guide
  - Update `docs/vg/vg-server/vg_security.md` - Encryption details
  - Update `server/docs/api.yaml` - OpenAPI spec

- [ ] **Task #18:** Write documentation for IP whitelist
  - `docs/vg/vg-server/vg_ip_whitelist_admin_guide.md` - Admin guide
  - `docs/vg/vg-client/vg_ip_whitelist_user_guide.md` - User guide
  - Update `docs/vg/vg-server/vg_security.md` - IP trust details
  - Update `server/docs/api.yaml` - OpenAPI spec

---

## Key Design Decisions

### Authentication Flow

**Current (preprocessors.js):**
1. Field Key (URL) → highest priority
2. Bearer token → API/app users
3. Basic auth → web users
4. Cookie → web users

**Changes:**
- **Cookie auth:** Add TOTP verification AFTER password, BEFORE session creation
- **Bearer auth:** Add IP whitelist check AFTER token validation, BEFORE authorization

### Two-Phase Login Flow

**Phase 1:** POST /v1/sessions
- Verify email/password
- If 2FA enabled: Create session with `totp_verified=false`
- Return `{ requireTotp: true }`

**Phase 2:** POST /v1/sessions/totp-verify
- Verify TOTP code or backup code
- Mark session `totp_verified=true`
- Return success

### Security

1. **TOTP Secret Encryption:**
   - AES-256-CBC with random IV
   - Key from `TOTP_ENCRYPTION_KEY` env var
   - Format: `"iv:ciphertext"` (both base64)

2. **Backup Code Hashing:**
   - Use bcrypt (same as passwords)
   - Never store plaintext
   - Display only once during setup/regeneration

3. **IP Spoofing Prevention:**
   - Trust first IP in X-Forwarded-For (set by nginx)
   - Never trust client-provided headers directly

4. **Rate Limiting:**
   - 5 failed TOTP attempts in 5 minutes → 15-minute lockout
   - Tracked in `vg_web_user_totp_attempts` table
   - IP-based for additional protection

### Database Schema

**TOTP Tables:**
- `vg_web_user_totp` - Encrypted secrets, enabled status
- `vg_web_user_totp_backup_codes` - Bcrypt-hashed backup codes, used_at tracking
- `vg_web_user_totp_attempts` - Rate limiting tracking

**IP Whitelist:**
- `vg_user_ip_whitelist` - PostgreSQL CIDR type for range matching

**Sessions:**
- Added `totp_verified` column (default true for backwards compatibility)

---

## Critical Files to Modify (Minimal Core Changes)

### Backend Core Files
- `server/lib/http/preprocessors.js` - Add 2FA check (Cookie), IP check (Bearer)
- `server/lib/resources/sessions.js` - Two-phase login

### Frontend Core Files
- `client/src/components/account/login.vue` - Add 2FA verification step

### New VG Files (No Upstream Conflicts)
- `server/lib/domain/vg-web-user-totp.js`
- `server/lib/model/query/vg-web-user-totp.js`
- `server/lib/model/query/vg-user-ip-whitelist.js`
- `server/lib/resources/vg-web-user-totp.js`
- `server/lib/resources/vg-user-ip-whitelist.js`
- `server/lib/util/vg-totp.js` ✅ DONE
- `client/src/components/user/edit/vg-totp-settings.vue`
- `client/src/components/user/edit/vg-ip-whitelist.vue`
- `client/src/components/vg/vg-totp-setup-modal.vue`

---

## Testing Commands

```bash
# Unit tests
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/util/vg-totp.js'

# Integration tests - TOTP
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-web-user-totp.js'

# Integration tests - IP Whitelist
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-user-ip-whitelist.js'
```

---

## Migration & Rollout Strategy

### Phased Rollout (Recommended)

1. **Week 1**: Deploy with `vg_web_user_totp_mandatory=false`
2. **Week 1-2**: Admins set up 2FA first
3. **Week 2**: Email all users: "2FA required in 30 days"
4. **Week 5**: Set `vg_web_user_totp_mandatory=true`
5. **Ongoing**: Users prompted to set up on next login

### Rollback Procedures

```sql
-- Disable 2FA globally
UPDATE vg_settings SET vg_key_value='false'
WHERE vg_key_name='vg_web_user_totp_mandatory';

-- Disable 2FA for specific user
UPDATE vg_web_user_totp SET totp_enabled=false
WHERE "actorId"=(SELECT "actorId" FROM users WHERE email='user@example.com');

-- Disable IP whitelist for user
DELETE FROM vg_user_ip_whitelist
WHERE "actorId"=(SELECT "actorId" FROM users WHERE email='user@example.com');
```

---

## Next Steps for Resume

1. **Continue Task #3**: Complete backend query modules and domain logic
2. **Test as you go**: Write unit tests alongside implementation
3. **Core file edits**: Modify preprocessors.js and sessions.js (document carefully)
4. **Frontend implementation**: Login flow, TOTP setup modal, settings UI
5. **Integration tests**: Full flow testing
6. **Documentation**: Admin and user guides

---

## Environment Variables Needed

```bash
# Add to docker-compose.yml or .env
TOTP_ENCRYPTION_KEY=<random-32-byte-key>  # For production, generate with: openssl rand -base64 32
```

---

## Reference Files

- Full implementation plan (detailed): Check previous plan mode transcript
- Existing VG patterns: `server/lib/domain/vg-app-user-auth.js`
- Existing query patterns: `server/lib/model/query/` (various files)
- Problem definitions: `server/lib/util/problem.js`

---

## Session End Checklist

- [ ] `bd sync` - Sync beads changes
- [ ] `git status` - Check what changed
- [ ] `git add` relevant files
- [ ] `git commit` with descriptive message
- [ ] `bd sync` again (in case beads changed)
- [ ] `git push` - Push to remote

**CRITICAL:** Work is NOT complete until `git push` succeeds.
