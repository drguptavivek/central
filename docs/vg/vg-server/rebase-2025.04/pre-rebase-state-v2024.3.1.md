# VG Server State: Pre-Rebase v2024.3.1 → v2025.4.0

**Snapshot Date:** 2026-01-12
**Backup Branch:** vg-work-pre-rebase-2025.4.0
**Current Commit:** 10b771d4 (Add: config/local.json to .gitignore)
**Base Version:** v2024.3.1 + 358 VG commits
**Repository:** https://github.com/drguptavivek/central-backend

---

## Executive Summary

This document captures the complete state of the VG server fork before rebasing onto upstream v2025.4.0. The VG fork includes extensive customizations for app-user authentication, session management, login security, Enketo status monitoring, and telemetry.

**Key Statistics:**
- VG commits ahead of v2024.3.1: **358 commits**
- Upstream commits to integrate: **274 commits** (v2024.3.2 → v2025.4.0)
- Risk level: **HIGH** (session management, auth, app-users conflicts expected)

---

## Recent VG Commits (Last 10)

```
10b771d4 Add: config/local.json to .gitignore
f158e49b Remove: config/local.json (not in upstream, use env vars instead)
c11814e6 Security: Remove hardcoded enketo API key from config
4b47a7b0 VG: Add Enketo Status API endpoints and backend logic
23d832fb VG: add login attempts remaining header
0b2d9e89 VG: add Retry-After header for web login lockouts
d75df840 VG: make web login lockout duration configurable
43d66e26 VG: harden web user login
3c666ee7 VG: relax project settings constraint for admin_pw
bb07f9bc VG: refresh project settings constraint in tests
```

---

## VG Feature Modules

### 1. App User Authentication (`vg-app-user-auth`)

**Core Files:**
- `lib/domain/vg-app-user-auth.js` (298 lines)
- `lib/model/query/vg-app-user-auth.js` (320 lines)
- `lib/resources/vg-app-user-auth.js` (358 lines)
- `lib/util/vg-password.js` (19 lines)
- `test/integration/api/vg-app-user-auth.js` (1,227 lines)

**Features:**
- Username/password authentication for app users
- Short-lived bearer token sessions (no long-lived tokens)
- Session TTL and cap enforcement via `vg_settings` table
- Login attempt tracking and lockout (5 failures → 10 min lock)
- Password complexity validation (min 10 chars, uppercase, lowercase, digit, special)
- QR code generation without embedded credentials

**Endpoints Added:**
- `POST /projects/:projectId/app-users/login`
- `POST /projects/:projectId/app-users/:id/password/reset`
- `POST /projects/:projectId/app-users/:id/password/change`
- `DELETE /projects/:projectId/app-users/:id/revoke` (non-admin)
- `DELETE /projects/:projectId/app-users/:id/revoke-admin` (admin)
- `POST /projects/:projectId/app-users/:id/active` (activate/deactivate)

**Database Tables:**
- `vg_field_key_auth` (stores username, password hash, phone, active status)
- `vg_app_user_login_attempts` (tracks failed login attempts)
- `vg_settings` (stores TTL/cap configuration)

### 2. Web User Login Hardening

**Modified Files:**
- `lib/http/sessions.js`
- `lib/resources/sessions.js`
- `test/integration/api/sessions.js`

**Features:**
- Web user login attempt tracking
- Configurable lockout duration (default 10 minutes)
- Rate limiting headers: `X-Login-Attempts-Remaining`, `Retry-After`
- Failed attempt counter reset on successful login

### 3. Session Management

**Modified Files:**
- `lib/model/query/sessions.js` (80 lines)
- `lib/resources/sessions.js`

**Key Changes in sessions.js:**
```javascript
// Line 20: Config-based session lifetime with custom expiry support
const expirySqlFragment = (expiresAt instanceof Date
  ? sql`${expiresAt.toISOString()}`
  : sql`statement_timestamp() + ${config.default.sessionLifetime + ' s'}::interval`);

// Line 45-47: Field key auth check with active status
left join vg_field_key_auth on vg_field_key_auth."actorId"=sessions."actorId"
where token=${token} and sessions."expiresAt" > now()
  and (actors.type <> 'field_key' or (vg_field_key_auth."actorId" is not null and vg_field_key_auth.vg_active = true))
```

**VG Session Features:**
- Project-level TTL/cap overrides (supports project-specific session policies)
- Session cap enforcement via `trimByActorId()`
- Custom TTL for app users (separate from web users)

### 4. Enketo Status Monitoring

**Core Files:**
- `lib/domain/vg-enketo-status.js`
- `lib/model/query/vg-enketo-status.js`
- `lib/resources/vg-enketo-status.js`
- `test/integration/api/vg-enketo-status*.js` (3 test files)

**Features:**
- Health check endpoint for Enketo service
- Status monitoring and reporting
- Integration tests for domain and API layers

### 5. Telemetry

**Core Files:**
- `lib/domain/vg-telemetry.js`
- `lib/model/query/vg-telemetry.js`
- `lib/resources/vg-telemetry.js`

**Features:**
- Usage tracking and metrics collection
- Telemetry data aggregation
- API endpoints for telemetry retrieval

### 6. Project Settings Enhancements

**Modified Files:**
- Various files supporting project-level configuration overrides

**Features:**
- Project admin password (`admin_pw`) setting
- Project-level session TTL/cap overrides
- Relaxed constraints to support VG-specific settings

---

## Database Schema

### VG-Specific Tables

**vg_field_key_auth:**
```sql
CREATE TABLE vg_field_key_auth (
  "actorId" INTEGER PRIMARY KEY REFERENCES actors(id),
  vg_username VARCHAR(255) UNIQUE NOT NULL,
  vg_password VARCHAR(255) NOT NULL,
  vg_phone VARCHAR(50),
  vg_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**vg_app_user_login_attempts:**
```sql
CREATE TABLE vg_app_user_login_attempts (
  id SERIAL PRIMARY KEY,
  "actorId" INTEGER REFERENCES actors(id),
  vg_username VARCHAR(255),
  attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  success BOOLEAN
);
```

**vg_settings:**
```sql
CREATE TABLE vg_settings (
  key VARCHAR(255) PRIMARY KEY,
  value JSONB,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**vg_project_settings:**
```sql
CREATE TABLE vg_project_settings (
  id SERIAL PRIMARY KEY,
  "projectId" INTEGER REFERENCES projects(id),
  setting_key VARCHAR(255),
  setting_value JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE ("projectId", setting_key)
);
```

### Migration Files

- `server/docs/sql/vg_app_user_auth.sql` (8,295 bytes)
  - Contains all VG table definitions and initial data
  - Applied manually to development and test databases

---

## Core File Modifications

### High-Risk Files (Upstream Conflicts Expected)

These files have been modified from upstream and are likely to conflict during rebase:

1. **lib/model/query/sessions.js** (server/lib/model/query/sessions.js:20,45-47)
   - Custom expiry logic with config-based lifetime
   - App user active status check in bearer token query

2. **lib/model/query/auth.js**
   - Password validation integration with VG password policy

3. **lib/resources/app-users.js**
   - Extended with VG auth endpoints
   - Modified create/list responses (no long-lived tokens)

4. **lib/resources/sessions.js**
   - Web user login hardening
   - Rate limiting integration

5. **test/integration/api/sessions.js**
   - Extended with web login lockout tests

6. **test/integration/api/app-users.js**
   - Modified to handle VG auth changes

### Low-Risk Files (VG-Only, No Conflicts Expected)

New files that shouldn't conflict with upstream:

- All `vg-*` prefixed files (domain, query, resources, tests)
- `lib/util/vg-password.js`

---

## Configuration

### Environment Variables (VG-Specific)

- `VG_APP_USER_SESSION_TTL_DAYS` - Default app user session TTL (days)
- `VG_APP_USER_SESSION_CAP` - Max concurrent sessions per app user
- `VG_WEB_LOGIN_LOCKOUT_MINUTES` - Web user lockout duration (default: 10)

### Config File Changes

- `config/local.json` added to `.gitignore` (security improvement)
- Hardcoded secrets removed (Enketo API key, S3 credentials)

---

## Test Coverage

### VG Test Files

1. **test/integration/api/vg-app-user-auth.js** (1,227 lines)
   - Comprehensive app user auth tests
   - Login, password reset/change, revoke, activate flows
   - Session TTL/cap enforcement
   - Login attempt tracking and lockouts

2. **test/integration/api/vg-enketo-status*.js** (3 files)
   - Enketo status monitoring tests
   - Domain and API layer coverage

3. **test/unit/util/vg-password.js**
   - Password policy validation tests
   - Complexity requirement tests

### Modified Upstream Tests

- `test/integration/api/sessions.js` - Extended with web login hardening tests
- `test/integration/api/app-users.js` - Modified for VG auth behavior

### Test Execution Commands

```bash
# VG password unit test
docker compose exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/util/vg-password.js'

# VG app user auth integration tests
docker compose exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-app-user-auth.js'

# VG Enketo status tests
docker compose exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-enketo-status.js'
```

---

## Known Issues and Technical Debt

1. **Manual SQL Migrations**
   - VG uses manual SQL migrations (`vg_app_user_auth.sql`)
   - Upstream uses Knex migrations
   - Conflict resolution needed: integrate VG schema into Knex migration chain

2. **Password Policy Layering**
   - VG password policy (`vg-password.js`) must layer on top of upstream validation
   - Upstream added 72-byte bcrypt limit (check compatibility)

3. **Session Management Isolation**
   - Must ensure VG app user session logic doesn't break upstream web user sessions
   - Config-based session lifetime (upstream PR #1586) must coexist with VG custom TTL

4. **Test Database Setup**
   - Manual SQL application required for test database
   - Should be integrated into test setup scripts

---

## Dependencies and Integrations

### Frontend Integration Points

VG server changes require corresponding frontend support:

- App user login UI (`/app-users/login`)
- System Settings UI (`/system/settings`)
- Project Settings overrides
- QR code display (credentials not embedded)

Frontend is on `vg-work` branch at v2025.4.0 + 38 VG commits (already up to date).

---

## Rebase Strategy

### Critical Success Factors

1. **Preserve all 358 VG commits** - Do NOT squash or skip
2. **Create backup branch** - ✅ Done: vg-work-pre-rebase-2025.4.0
3. **Sequential conflict resolution** - Follow Phase 2 plan
4. **Test before push** - Run all VG tests + upstream tests
5. **Force-push with --force-with-lease** - Preserve safety

### Rollback Plan

If critical issues arise during rebase:

```bash
cd server
git reset --hard vg-work-pre-rebase-2025.4.0
git push --force-with-lease origin vg-work
```

---

## Post-Rebase Verification Checklist

After rebase completes, verify:

- [ ] All VG tests pass (app-user auth, enketo status, telemetry)
- [ ] All upstream tests pass
- [ ] App user login/logout flows work
- [ ] Session TTL/cap enforcement works
- [ ] Password reset/change flows work
- [ ] QR code generation works (no embedded credentials)
- [ ] Login attempt tracking and lockouts work
- [ ] Enketo Status page loads
- [ ] System Settings UI works
- [ ] Project settings overrides work
- [ ] No regressions in upstream features
- [ ] Database migrations apply cleanly

---

## References

- **Plan Document:** docs/vg/vg-server/rebase-v2025.4.0-plan.md
- **Beads Epic:** central-xav (22 subtasks)
- **GitHub Issue:** https://github.com/drguptavivek/central/issues/98
- **Parent Issue:** central-m56
- **Upstream Release:** https://github.com/getodk/central/releases/tag/v2025.4.1
- **VG Server Fork:** https://github.com/drguptavivek/central-backend
- **Backup Branch:** vg-work-pre-rebase-2025.4.0

---

**Document Status:** Complete
**Next Phase:** P1.1-P1.3 (Pre-Rebase Analysis)
**Tasks Ready:** 5 tasks (Phase 1 analysis can begin)
