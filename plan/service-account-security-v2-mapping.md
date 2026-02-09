# Plan Mapping: API Token Management & Service Account Security

> **Generated:** 2026-02-09
> **Maps:** `service-account-security-v2.md` → Existing Beads Issues

---

## Current Beads Status

**Total Issues:** 162 (15 open, 0 in progress, 10 ready, 147 closed)

---

## 1. Foundation Work (ALREADY COMPLETE ✅)

### ✅ `central-1hu` - TOTP 2FA + IP Whitelist for ODK Central (CLOSED)
**Status:** Backend ✅ Complete, Frontend ✅ Mostly Complete

**Provides Foundation For:**
- ✅ TOTP infrastructure (required for API token creation security)
- ✅ IP whitelist infrastructure (required for service account enforcement)
- ✅ Database tables: `vg_web_user_totp`, `vg_user_ip_whitelist`
- ✅ Core file modifications: `preprocessors.js`, `sessions.js`

**Plan Dependencies:**
- Part 1 (API Tokens): Requires TOTP verification when creating tokens → **AVAILABLE**
- Part 2 (Service Accounts): Requires IP whitelist enforcement → **AVAILABLE**

---

## 2. Active Work (IN PROGRESS 🔄)

### 🔄 `central-2y6` - EPIC: Role-Based TOTP 2FA Enrollment System (OPEN)
**Status:** Open with 13 subtasks (5 blocked)
**Priority:** P1
**Owner:** Dr Vivek Gupta

**Subtasks:**
- `central-ins`: Frontend: Update login component for enrollment flags (READY)
- `central-vdl`: Frontend: Create mandatory enrollment modal (blocked by central-ins)
- `central-fyl`: Frontend: Create optional enrollment prompt modal (READY)
- `central-nbb`: Frontend: Create system settings UI for mandatory roles (READY)
- `central-iso`: Frontend: Integrate enrollment modals in home component (blocked)
- `central-5w2`: Integration testing: Full enrollment flow coverage (blocked)
- `central-tbg`: Documentation: Update VG docs with enrollment feature (blocked)
- Plus 6 testing tasks (ready): central-94t, central-4km, central-2g2, central-3ii, central-ndz, central-5sm

**Relationship to New Plan:**
- **INDEPENDENT** - Enrollment system is a separate feature
- **NO CONFLICTS** - Can proceed in parallel
- **SUGGESTED ORDER:**
  1. Complete enrollment work first (already in progress)
  2. Then start API token + service account work

---

## 3. New Work Required (NOT YET TRACKED ❌)

The following work from `service-account-security-v2.md` has **NO existing Beads issues**:

### 🆕 Part 1: API Token Management System

**NOT TRACKED - Needs New Issues:**

| Plan Section | Work Required | Beads Issue | Status |
|--------------|---------------|-------------|--------|
| **Database** | Migration `20260209-01-vg-api-tokens.*` | ❌ None | Not created |
| **Backend Models** | `lib/model/query/vg-api-tokens.js` | ❌ None | Not created |
| **Backend Frames** | `lib/model/frames/vg-api-token.js` | ❌ None | Not created |
| **Backend Routes** | `lib/resources/vg-api-tokens.js` | ❌ None | Not created |
| **Core Edits** | Update `preprocessors.js` for token auth | ❌ None | Not created |
| **Tests** | `test/integration/api/vg-api-tokens.js` | ❌ None | Not created |
| **Frontend UI** | `vg-api-tokens.vue` component | ❌ None | Not created |
| **Docs** | Route docs, admin guides | ❌ None | Not created |

### 🆕 Part 2: Service Account System

**NOT TRACKED - Needs New Issues:**

| Plan Section | Work Required | Beads Issue | Status |
|--------------|---------------|-------------|--------|
| **Database** | Migration `20260209-02-vg-service-accounts.*` | ❌ None | Not created |
| **Backend Models** | Update `users.js` query module | ❌ None | Not created |
| **Backend Frames** | Add `isServiceAccount` to `user.js` frame | ❌ None | Not created |
| **Backend Routes** | `lib/resources/vg-service-users.js` | ❌ None | Not created |
| **Core Edits** | Update `sessions.js` for 1hr lifetime | ❌ None | Not created |
| **Core Edits** | Update `preprocessors.js` for mandatory IP check | ❌ None | Not created |
| **Tests** | `test/integration/api/vg-service-accounts.js` | ❌ None | Not created |
| **Frontend UI** | `vg-service-account.vue` component | ❌ None | Not created |
| **Docs** | Route docs, admin guides | ❌ None | Not created |

---

## 4. Recommended Action Plan

### Option A: Sequential (Recommended for TDD Focus)
```
1. Complete TOTP enrollment work (central-2y6 epic)
   → 10 issues ready, clear focus

2. Create and implement API Token issues (Part 1)
   → Build on solid TOTP foundation
   → ~9 new issues needed

3. Create and implement Service Account issues (Part 2)
   → Build on API token foundation
   → ~9 new issues needed
```

### Option B: Parallel (If Multiple Developers)
```
Developer 1: Complete TOTP enrollment (central-2y6)
Developer 2: Implement API tokens (Part 1)
Developer 3: Implement Service accounts (Part 2)

Sync point: Integration testing
```

### Option C: Immediate Start (New Plan Priority)
```
1. Create ALL Beads issues for service-account-security-v2.md
   → Estimated 18-20 new issues

2. Start Part 1 (API Tokens) immediately
   → Leave enrollment work for later

3. Continue to Part 2 (Service Accounts)
   → Complete new security features first
```

---

## 5. Issue Creation Checklist

If proceeding with new plan, create these epics + subtasks:

### Epic 1: API Token Management
- [ ] `EPIC: API Token Management System`
  - [ ] Design API contract
  - [ ] Create `vg_api_tokens` migration
  - [ ] Implement `VgApiTokens` query module (TDD)
  - [ ] Implement POST `/v1/users/:id/api-tokens` (TDD)
  - [ ] Implement GET `/v1/users/:id/api-tokens` (TDD)
  - [ ] Implement DELETE `/v1/users/:id/api-tokens/:tokenId` (TDD)
  - [ ] Update `preprocessors.js` for API token auth (TDD)
  - [ ] Document routes in `vg-service-users.md`
  - [ ] Document core edits in `vg_core_server_edits.md`

### Epic 2: Service Account System
- [ ] `EPIC: Service Account Security System`
  - [ ] Create service account migration
  - [ ] Add `isServiceAccount` to User frame
  - [ ] Implement PATCH `/v1/users/:id/service-account` (TDD)
  - [ ] Update `sessions.js` for 1hr service account lifetime (TDD)
  - [ ] Update `preprocessors.js` for mandatory IP whitelist (TDD)
  - [ ] Document routes in `vg-service-users.md`
  - [ ] Document core edits in `vg_core_server_edits.md`

### Epic 3: Frontend UI (After Backend Complete)
- [ ] `EPIC: Token & Service Account UI`
  - [ ] Build `vg-api-tokens.vue` component
  - [ ] Build `vg-service-account.vue` component
  - [ ] Integration with user edit page
  - [ ] E2E tests
  - [ ] User documentation

**Total Estimated Issues:** ~20 (2 epics + 18 tasks)

---

## 6. Dependency Analysis

### Dependencies on Existing Work
✅ **TOTP Infrastructure** (from central-1hu)
- API token creation requires TOTP verification
- **Available:** TOTP verification endpoints exist

✅ **IP Whitelist Infrastructure** (from central-1hu)
- Service accounts require IP whitelist enforcement
- **Available:** IP whitelist tables and checks exist

### No Blocking Dependencies
- New plan can start immediately
- Enrollment work (central-2y6) is independent
- **Recommendation:** Complete enrollment first for cleaner focus

---

## 7. Summary

| Category | Count | Status |
|----------|-------|--------|
| **Foundation work** | 1 epic | ✅ Complete (central-1hu) |
| **Active work** | 1 epic + 13 tasks | 🔄 In progress (central-2y6) |
| **New work needed** | 2 epics + ~18 tasks | ❌ Not yet tracked |
| **Total new issues to create** | ~20 | Ready to create |

**Recommendation:**
1. Decide priority: Complete enrollment first OR start new plan immediately
2. Create Beads issues for new plan (use parallel subagents for efficiency)
3. Follow TDD workflow as outlined in plan
4. Maintain VG modularity throughout

---

## Next Steps

**User Decision Required:**

1. **Continue enrollment work first?** (central-2y6 → 10 issues ready)
2. **Start API tokens immediately?** (create new issues, begin implementation)
3. **Create all issues now, implement later?** (planning phase)

**Ready to execute any option immediately.**
