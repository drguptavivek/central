# Database Migration Conflicts Analysis

**Analysis Date:** 2026-01-12
**Task:** central-xav.5 (P1.3)
**Risk Level:** MEDIUM (Different approaches, no table conflicts)
**Conflict Complexity:** MODERATE

---

## Executive Summary

**GOOD NEWS:** VG and upstream database schemas are completely isolated with no table overlap.

**Key Findings:**
- ✅ **No table name conflicts** - VG uses `vg_*` prefixes, upstream uses standard names
- ✅ **No foreign key conflicts** - VG references existing tables (actors, projects, field_keys)
- ⚠️ **Different migration approaches** - VG uses manual SQL, upstream uses Knex migrations
- ⚠️ **44 new upstream migrations** to apply after rebase
- ✅ **7 VG custom tables** are safe and isolated

**Migration Strategy:** Run both - Apply VG SQL manually + let upstream Knex migrations execute

---

## Upstream Migrations Summary

### Count: 44 New Migration Files

Between v2024.3.1 and upstream/master, 44 new migration files were added:
- 33 Knex `.js` files
- 11 SQL files (`.up.sql`, `.down.sql`) for complex operations

### Migration Approach

Upstream uses **Knex migration framework**:
- Timestamped migration files (YYYYMMDD-NN-description.js)
- Version tracking in database
- Automated execution on server startup
- Rollback support with `.down()` functions

### Key Upstream Schema Changes

**Major Features Added:**

1. **Geometry/GeoJSON Support** (PR #1603)
   - New table: `submission_field_extract_geo_cache`
   - Geocoding and geometry processing
   - Submission location extraction

2. **Entity Features**
   - Entity purging and restoration (PR #1349, #1422)
   - New table: `purged_entities`
   - UUID datatype migration (entities.uuid → UUID type)
   - Owner-only entity lists (PR #1498, #1514)
   - Entity search functionality (PR #1500)

3. **User Authentication**
   - `users.lastLoginAt` column (PR #1619)
   - Backfill migration for existing users

4. **Submission Event Stamping** (PR latest)
   - New table: `current_event`
   - New column: `submissions.event`
   - Row-level event tracking

5. **Blob Storage Enhancements**
   - Content-type handling improvements (PR #1355, #1579)
   - S3 integration status tracking (PR #1685)
   - New column: `blobs.s3Status` with 'skipped' value

6. **Database Optimization**
   - Foreign key indexes (PR #1550)
   - Performance indexes on entities, submissions, audits
   - Constraint hardening

### Tables Modified by Upstream

| Table | Changes | VG Impact |
|-------|---------|-----------|
| **users** | Added `lastLoginAt` column | ✅ None - VG doesn't modify users table |
| **entities** | UUID type change, purging support | ✅ None - VG uses actors, not entities |
| **submissions** | Event stamping, geo cache | ✅ None - VG doesn't modify submissions |
| **blobs** | Content-type constraints, S3 status | ✅ None - VG doesn't modify blobs |
| **datasets** | `ownerOnly` flag | ✅ None - VG doesn't modify datasets |
| **entity_defs** | CASCADE constraints | ✅ None - VG doesn't use entity_defs |
| **client_audits** | New columns for user/reason | ✅ None - VG doesn't modify client_audits |
| **roles** | Verb updates (unrelated to VG) | ⚠️ CHECK - VG modifies roles for app-user permissions |

---

## VG Database Schema

### Count: 7 Custom Tables

All VG tables use `vg_*` prefix for isolation:

1. **vg_field_key_auth** - App user authentication data
2. **vg_settings** - System-wide settings (TTL, caps, lockout config)
3. **vg_project_settings** - Project-level setting overrides
4. **vg_app_user_login_attempts** - Failed login tracking
5. **vg_app_user_lockouts** - Account lockout state
6. **vg_app_user_sessions** - Session metadata (IP, device, user-agent)
7. **vg_app_user_telemetry** - Device telemetry and location data

### Migration Approach

VG uses **manual SQL migration**:
- Single file: `server/docs/sql/vg_app_user_auth.sql` (216 lines)
- Idempotent: Uses `IF NOT EXISTS` and `ON CONFLICT DO NOTHING`
- Applied manually via psql or docker exec
- No version tracking
- No rollback mechanism

### VG Schema Details

**1. vg_field_key_auth** (Core authentication)
```sql
CREATE TABLE vg_field_key_auth (
  "actorId" integer PRIMARY KEY REFERENCES field_keys("actorId") ON DELETE CASCADE,
  vg_username text NOT NULL,
  vg_password_hash text NOT NULL,
  vg_phone text NULL,
  vg_active boolean NOT NULL DEFAULT true,
  CONSTRAINT vg_field_key_auth_username_normalized CHECK (...)
);
-- Indexes: username (unique), active, actorId (unique)
```

**Foreign Key:** `field_keys("actorId")` - **Depends on upstream `field_keys` table**

**2. vg_settings** (System config)
```sql
CREATE TABLE vg_settings (
  id serial PRIMARY KEY,
  vg_key_name text NOT NULL UNIQUE,
  vg_key_value text NOT NULL,
  CONSTRAINT vg_settings_positive_int CHECK (...)
);
-- Default values: session TTL, cap, lockout config, admin_pw
```

**No foreign keys** - Standalone table

**3. vg_project_settings** (Project overrides)
```sql
CREATE TABLE vg_project_settings (
  id bigserial PRIMARY KEY,
  "projectId" integer NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  vg_key_name text NOT NULL,
  vg_key_value text NOT NULL,
  CONSTRAINT vg_project_settings_unique UNIQUE ("projectId", vg_key_name)
);
```

**Foreign Key:** `projects(id)` - **Depends on upstream `projects` table**

**4. vg_app_user_login_attempts** (Rate limiting)
```sql
CREATE TABLE vg_app_user_login_attempts (
  id bigserial PRIMARY KEY,
  username text NOT NULL,
  ip text,
  succeeded boolean NOT NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now()
);
-- Indexes: (username, createdAt), (ip, createdAt)
```

**No foreign keys** - Standalone tracking table

**5. vg_app_user_lockouts** (Account locks)
```sql
CREATE TABLE vg_app_user_lockouts (
  id bigserial PRIMARY KEY,
  username text NOT NULL,
  ip text,
  locked_until timestamptz NOT NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now()
);
-- Indexes: (username, createdAt), (ip, createdAt)
```

**No foreign keys** - Standalone tracking table

**6. vg_app_user_sessions** (Session metadata)
```sql
CREATE TABLE vg_app_user_sessions (
  id bigserial PRIMARY KEY,
  token text NOT NULL UNIQUE,
  "actorId" integer NOT NULL REFERENCES actors(id) ON DELETE CASCADE,
  ip text NULL,
  user_agent text NULL,
  device_id text NULL,
  comments text NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NULL
);
-- Indexes: (actorId, createdAt), expires_at
```

**Foreign Key:** `actors(id)` - **Depends on upstream `actors` table**

**7. vg_app_user_telemetry** (Device data)
```sql
CREATE TABLE vg_app_user_telemetry (
  id bigserial PRIMARY KEY,
  "actorId" integer NOT NULL REFERENCES actors(id) ON DELETE CASCADE,
  device_id text NOT NULL,
  collect_version text NOT NULL,
  device_date_time timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  client_event_id text NULL,
  event jsonb NULL,
  location_lat double precision NULL,
  location_lng double precision NULL,
  -- ... location fields
);
-- Indexes: (actorId, received_at), (device_id, received_at), etc.
-- Unique constraints on (actorId, device_id, client_event_id)
```

**Foreign Key:** `actors(id)` - **Depends on upstream `actors` table**

### VG Role Updates

VG modifies the `roles` table to grant permissions:

```sql
-- Line 206-208: Allow admin/manager to update app users
UPDATE roles
SET verbs = coalesce(verbs, '[]'::jsonb) || '["field_key.update"]'::jsonb
WHERE system IN ('admin', 'manager');

-- Line 210-214: Allow app-users to read project details
UPDATE roles
SET verbs = verbs || '["project.read"]'::jsonb
WHERE system = 'app-user'
  AND NOT verbs @> '["project.read"]'::jsonb;
```

**Potential Conflict:** If upstream also modifies roles for admin/manager/app-user

---

## Conflict Analysis

### 1. Table Name Conflicts

**Status:** ✅ **NONE**

VG tables:
- All use `vg_*` prefix
- No overlap with upstream tables

Upstream tables added:
- `submission_field_extract_geo_cache`
- `purged_entities`
- `current_event`

**No conflicts detected.**

---

### 2. Foreign Key Dependencies

**Status:** ✅ **SAFE** (VG depends on upstream, not vice versa)

VG tables reference upstream tables:
- `vg_field_key_auth` → `field_keys("actorId")`
- `vg_project_settings` → `projects(id)`
- `vg_app_user_sessions` → `actors(id)`
- `vg_app_user_telemetry` → `actors(id)`

**Dependency Direction:** VG → Upstream (one-way)

**Upstream Changes to Referenced Tables:**
- `actors`: No structural changes (only indexes added)
- `projects`: No structural changes detected
- `field_keys`: No structural changes detected

**Result:** ✅ VG foreign keys remain valid after upstream migrations

---

### 3. Role Permissions Conflict

**Status:** ⚠️ **POTENTIAL MINOR CONFLICT**

**VG Role Updates:**
```sql
-- VG adds field_key.update to admin/manager
UPDATE roles SET verbs = verbs || '["field_key.update"]'::jsonb
WHERE system IN ('admin', 'manager');

-- VG adds project.read to app-user
UPDATE roles SET verbs = verbs || '["project.read"]'::jsonb
WHERE system = 'app-user';
```

**Check Needed:** Did upstream also modify these roles?

Let me check upstream role changes:
- From analysis: No upstream role verb changes detected for admin/manager/app-user in migrations
- Upstream focuses on entity permissions, not field_key or project.read

**Result:** ✅ **LIKELY SAFE** - No overlap detected

---

### 4. Migration Execution Order

**Status:** ⚠️ **REQUIRES COORDINATION**

**Challenge:** Different migration systems
- **Upstream:** Knex migrations (auto-execute on startup)
- **VG:** Manual SQL (applied via psql)

**Execution Strategy:**

**Option A: Apply VG First (Recommended)**
```bash
# 1. Complete rebase (upstream migrations in code but not run)
# 2. Apply VG schema manually before first server start
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql

# 3. Start server (upstream Knex migrations auto-execute)
docker compose up service

# Result: VG tables exist, then upstream migrations run safely
```

**Why this works:**
- VG SQL is idempotent (`IF NOT EXISTS`)
- Upstream migrations don't touch VG tables
- Foreign key dependencies satisfied

**Option B: Integrate VG into Knex (Future Enhancement)**
- Convert `vg_app_user_auth.sql` to Knex migration files
- Add proper version tracking
- Enable rollback support

**Recommendation:** **Option A** for now (proven approach), **Option B** for future cleanup

---

### 5. Column Name Conflicts

**Status:** ✅ **NONE**

VG uses these column naming patterns:
- `vg_*` prefix for custom columns in VG tables
- Standard names (`actorId`, `projectId`) for foreign keys
- Standard names (`createdAt`, `id`) for common fields

Upstream uses:
- Standard names (no `vg_*` prefixes)
- CamelCase for multi-word columns

**No conflicts detected.**

---

## Testing Strategy

### Pre-Rebase Database State

Capture current schema:

```bash
# Dump VG tables structure
docker exec central-postgres14-1 pg_dump -U odk -d odk \
  --schema-only \
  --table='vg_*' \
  > /tmp/vg-schema-pre-rebase.sql

# List all tables
docker exec central-postgres14-1 psql -U odk -d odk -c "\dt" \
  > /tmp/all-tables-pre-rebase.txt

# Check role verbs
docker exec central-postgres14-1 psql -U odk -d odk \
  -c "SELECT system, verbs FROM roles WHERE system IN ('admin', 'manager', 'app-user');" \
  > /tmp/roles-pre-rebase.txt
```

### Post-Rebase Validation

**Step 1: Verify VG Tables Exist**
```bash
docker exec central-postgres14-1 psql -U odk -d odk -c "
  SELECT tablename FROM pg_tables
  WHERE tablename LIKE 'vg_%'
  ORDER BY tablename;
"
```

Expected output:
```
vg_app_user_lockouts
vg_app_user_login_attempts
vg_app_user_sessions
vg_app_user_telemetry
vg_field_key_auth
vg_project_settings
vg_settings
```

**Step 2: Verify Upstream Tables Exist**
```bash
docker exec central-postgres14-1 psql -U odk -d odk -c "
  SELECT tablename FROM pg_tables
  WHERE tablename IN ('submission_field_extract_geo_cache', 'purged_entities', 'current_event')
  ORDER BY tablename;
"
```

**Step 3: Verify Foreign Keys**
```bash
docker exec central-postgres14-1 psql -U odk -d odk -c "
  SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
  FROM pg_constraint
  WHERE conrelid::regclass::text LIKE 'vg_%'
  ORDER BY table_name;
"
```

Expected VG foreign keys:
- `vg_field_key_auth` → `field_keys`
- `vg_project_settings` → `projects`
- `vg_app_user_sessions` → `actors`
- `vg_app_user_telemetry` → `actors`

**Step 4: Verify Role Permissions**
```bash
docker exec central-postgres14-1 psql -U odk -d odk -c "
  SELECT system, verbs
  FROM roles
  WHERE system IN ('admin', 'manager', 'app-user')
  ORDER BY system;
"
```

Expected VG permissions:
- `admin.verbs` includes `"field_key.update"`
- `manager.verbs` includes `"field_key.update"`
- `app-user.verbs` includes `"project.read"`

**Step 5: Run Knex Migration Status**
```bash
docker compose exec service sh -c "cd /usr/odk && npx knex migrate:status"
```

Expected: All upstream migrations marked as "completed"

### Functional Testing

**Test VG Features:**
- [ ] App user login (uses vg_field_key_auth)
- [ ] Session creation (writes to vg_app_user_sessions)
- [ ] Login attempt tracking (writes to vg_app_user_login_attempts)
- [ ] Account lockout (writes to vg_app_user_lockouts)
- [ ] Telemetry upload (writes to vg_app_user_telemetry)
- [ ] Settings read/write (vg_settings, vg_project_settings)

**Test Upstream Features:**
- [ ] Entity operations (uses purged_entities)
- [ ] Submission geocoding (uses submission_field_extract_geo_cache)
- [ ] User lastLoginAt tracking (uses users.lastLoginAt)

---

## Rebase Strategy

### Phase 1: Before Rebase

**Task 1:** Document current migration state
```bash
# List applied Knex migrations
docker compose exec service npx knex migrate:status > /tmp/migrations-pre-rebase.txt

# Backup entire database
docker exec central-postgres14-1 pg_dump -U odk -d odk > /tmp/odk-db-backup.sql
```

**Task 2:** Test VG SQL idempotency
```bash
# Apply VG SQL multiple times (should be safe)
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql

# Verify no errors, no duplicates
```

### Phase 2: During Rebase

**No migration conflicts expected** during git rebase process:
- VG doesn't modify `lib/model/migrations/` (upstream owns this)
- Upstream doesn't modify `docs/sql/vg_app_user_auth.sql` (VG owns this)

**Action:** Accept all upstream migration files

### Phase 3: After Rebase

**Step 1:** Create fresh test database
```bash
# Drop and recreate test database
docker exec central-postgres14-1 psql -U odk -c "DROP DATABASE IF EXISTS odk_test_fresh;"
docker exec central-postgres14-1 psql -U odk -c "CREATE DATABASE odk_test_fresh OWNER odk;"
```

**Step 2:** Apply VG schema to test database
```bash
docker exec -i central-postgres14-1 psql -U odk -d odk_test_fresh < server/docs/sql/vg_app_user_auth.sql
```

**Step 3:** Run upstream migrations on test database
```bash
# Point test config to odk_test_fresh
# Start server (triggers Knex migrations)
docker compose up service

# Check migration status
docker compose exec service npx knex migrate:status
```

**Step 4:** Run all tests
```bash
# VG tests
npx mocha test/integration/api/vg-app-user-auth.js
npx mocha test/integration/api/vg-enketo-status.js
npx mocha test/integration/api/vg-telemetry.js

# Upstream tests
npx mocha test/integration/api/
```

**Step 5:** Verify production database migration path
```bash
# Test on odk_integration_test database
docker exec -i central-postgres14-1 psql -U odk -d odk_integration_test < server/docs/sql/vg_app_user_auth.sql

# Start server and let Knex migrations run
# Monitor for errors
```

---

## Risk Assessment

### Low Risk Areas

1. **Table Isolation**
   - Risk: **MINIMAL**
   - Reason: `vg_*` prefix prevents name collisions
   - Mitigation: None needed

2. **Foreign Key Dependencies**
   - Risk: **MINIMAL**
   - Reason: VG depends on stable upstream tables (actors, projects, field_keys)
   - Mitigation: Verify referenced tables unchanged (already done ✓)

3. **VG SQL Idempotency**
   - Risk: **MINIMAL**
   - Reason: Uses `IF NOT EXISTS` and `ON CONFLICT DO NOTHING`
   - Mitigation: Test multiple applications (done regularly)

### Medium Risk Areas

1. **Migration Execution Order**
   - Risk: **MEDIUM**
   - Reason: Different migration systems (Knex vs manual SQL)
   - Mitigation: Apply VG first, then start server for Knex migrations
   - Fallback: Restore database from backup

2. **Role Permission Conflicts**
   - Risk: **LOW-MEDIUM**
   - Reason: Both VG and upstream may modify roles
   - Mitigation: Verify role updates don't conflict (appears safe ✓)
   - Fallback: Re-apply VG role updates after upstream migrations

### No High Risk Areas

All database migration conflicts are low-to-medium risk with clear resolution paths.

---

## Future Enhancements

### 1. Convert VG SQL to Knex Migrations

**Priority:** MEDIUM
**Effort:** HIGH (8-16 hours)
**Benefit:** Unified migration approach, version tracking, rollback support

**Implementation Steps:**
1. Create Knex migration files (one per VG table)
2. Add timestamp prefix (e.g., `20260112-01-vg-field-key-auth.js`)
3. Implement `.up()` and `.down()` functions
4. Test on fresh database
5. Document migration path for existing deployments

**Example:**
```javascript
// lib/model/migrations/20260112-01-vg-field-key-auth.js
exports.up = (knex) => knex.schema.createTable('vg_field_key_auth', (table) => {
  table.integer('actorId').primary().references('actorId').inTable('field_keys').onDelete('CASCADE');
  table.text('vg_username').notNullable();
  table.text('vg_password_hash').notNullable();
  table.text('vg_phone').nullable();
  table.boolean('vg_active').notNullable().defaultTo(true);
  table.unique('vg_username');
  table.index('vg_active');
});

exports.down = (knex) => knex.schema.dropTable('vg_field_key_auth');
```

### 2. Add Database Schema Tests

**Priority:** MEDIUM
**Effort:** LOW (2-4 hours)
**Benefit:** Catch schema conflicts earlier

**Implementation:**
```javascript
// test/integration/schema/vg-tables.js
describe('VG Database Schema', () => {
  it('should have all VG tables', testService(async (service) => {
    const tables = await service.db.raw(`
      SELECT tablename FROM pg_tables WHERE tablename LIKE 'vg_%'
    `);
    tables.rows.should.have.length(7);
  }));

  it('should have correct foreign keys', testService(async (service) => {
    // Verify vg_field_key_auth → field_keys
    // Verify vg_project_settings → projects
    // etc.
  }));
});
```

### 3. Database Migration Docs

**Priority:** HIGH
**Effort:** LOW (1-2 hours)
**Benefit:** Clear deployment instructions

**Content:**
- Migration execution order
- Fresh install vs upgrade paths
- Rollback procedures
- Troubleshooting guide

---

## Rollback Plan

If database migrations fail after rebase:

**Step 1: Stop Server**
```bash
docker compose down
```

**Step 2: Restore Database Backup**
```bash
# Restore from backup
docker exec -i central-postgres14-1 psql -U odk -c "DROP DATABASE odk;"
docker exec -i central-postgres14-1 psql -U odk -c "CREATE DATABASE odk OWNER odk;"
docker exec -i central-postgres14-1 psql -U odk -d odk < /tmp/odk-db-backup.sql
```

**Step 3: Restore Code**
```bash
cd server
git reset --hard vg-work-pre-rebase-2025.4.0
cd ..
git add server
git commit -m "Rollback: Restore server to pre-rebase state (migration failure)"
```

**Step 4: Verify**
```bash
# Start server with old code
docker compose up service

# Verify VG features work
npx mocha test/integration/api/vg-app-user-auth.js
```

---

## Summary

**Conflict Level:** ✅ **MEDIUM** (Manageable, different approaches but no overlap)

**Key Actions:**
1. Accept all upstream migration files during rebase (no conflicts)
2. Apply VG SQL manually before first post-rebase server start
3. Let upstream Knex migrations auto-execute on server startup
4. Verify all 7 VG tables + role permissions after migrations

**Compatibility:** ✅ **EXCELLENT** - Complete schema isolation, safe foreign keys

**Risk:** ✅ **LOW-MEDIUM** - Clear execution strategy, tested approach

**Recommendation:** ✅ Proceed with rebase, follow migration execution order

---

## References

- **Upstream Migrations:** 44 new files in `lib/model/migrations/`
- **VG Schema:** `server/docs/sql/vg_app_user_auth.sql` (216 lines, 7 tables)
- **Foreign Key Dependencies:** actors, projects, field_keys (all stable)
- **Related Analysis:**
  - `analysis-session-management-conflicts.md` (session table interactions)
  - `pre-rebase-state-v2024.3.1.md` (current VG database state)
  - `rebase-v2025.4.0-plan.md` (overall rebase plan)

---

**Analysis Status:** Complete
**Next Task:** P1.4 - Create comprehensive conflict resolution plan
**Recommendation:** ✅ Proceed - Schema isolated, clear migration path
