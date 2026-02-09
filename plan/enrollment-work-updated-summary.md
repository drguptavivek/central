# Enrollment Work: Updated Summary with Service Account Support

> **Updated:** 2026-02-09
> **Status:** Ready to proceed (backend complete, 4 new tasks added)

---

## Summary

**NEW:** Added 4 tasks for service account exclusion support
**RESULT:** Enrollment epic now has 17 total tasks (was 13)
**READY:** 12 tasks ready to work (was 10)

---

## Added Tasks (Service Account Support)

| ID | Title | Priority | Status | Blocked By |
|----|-------|----------|--------|------------|
| central-7oo | Backend: Exclude service accounts from shouldPromptEnrollment() | P2 | ✅ READY | None |
| central-g1f | Backend: Exclude service accounts from isRoleMandatoryForTotp() | P2 | ✅ READY | None |
| central-b5k | Test: Service account excluded from enrollment prompts | P2 | 🔒 Blocked | central-7oo, central-g1f |
| central-mox | Docs: Document service account exclusion from enrollment | P2 | 🔒 Blocked | central-b5k |

**Dependencies:**
```
central-7oo (READY)
    ↓
central-g1f (READY)
    ↓
central-b5k (blocked by both above)
    ↓
central-mox (blocked by b5k)
```

---

## Full Enrollment Epic Status

### Epic: central-2y6 - Role-Based TOTP 2FA Enrollment System (P1)

**Backend (7 tasks) - ✅ 5 CLOSED, 🆕 2 READY**

| ID | Title | Status |
|----|-------|--------|
| central-cbq | DB Migration: Add TOTP enrollment tracking + mandatory roles setting | ✅ CLOSED |
| central-wge | Backend: Add TOTP query module methods | ✅ CLOSED |
| central-2fm | Backend: Modify sessions resource for enrollment checks | ✅ CLOSED |
| central-592 | Backend: Add dismiss enrollment prompt endpoint | ✅ CLOSED |
| central-bt7 | Backend: Add system settings endpoints for mandatory roles | ✅ CLOSED |
| **central-7oo** | **Backend: Exclude service accounts from shouldPromptEnrollment()** | **🆕 READY** |
| **central-g1f** | **Backend: Exclude service accounts from isRoleMandatoryForTotp()** | **🆕 READY** |

**Frontend (7 tasks) - ✅ READY (3 unblocked)**

| ID | Title | Status | Blocked By |
|----|-------|--------|------------|
| central-ins | Frontend: Update login component for enrollment flags | ✅ READY | ~~central-2fm~~ (closed) |
| central-vdl | Frontend: Create mandatory enrollment modal | 🔒 Blocked | central-ins |
| central-fyl | Frontend: Create optional enrollment prompt modal | ✅ READY | ~~central-592~~ (closed) |
| central-iso | Frontend: Integrate enrollment modals in home component | 🔒 Blocked | central-fyl, central-vdl |
| central-nbb | Frontend: Create system settings UI for mandatory roles | ✅ READY | ~~central-bt7~~ (closed) |
| central-901 | Backend: System settings API for mandatory roles | ❓ Check status |
| central-903 | Frontend: Enrollment flow integration | ❓ Check status |

**Testing & Docs (3 tasks) - 🔒 Mostly Blocked**

| ID | Title | Status | Blocked By |
|----|-------|--------|------------|
| **central-b5k** | **Test: Service account excluded from enrollment prompts** | **🆕 Blocked** | central-7oo, central-g1f |
| central-5w2 | Integration testing: Full enrollment flow coverage | 🔒 Blocked | Multiple frontend |
| central-tbg | Documentation: Update VG docs with enrollment feature | 🔒 Blocked | central-5w2 |
| **central-mox** | **Docs: Document service account exclusion from enrollment** | **🆕 Blocked** | central-b5k |

---

## Current Ready Tasks (12 total)

### Priority 1: Enrollment Work (5 tasks)

1. **central-7oo** (P2) - Backend: Exclude service accounts from shouldPromptEnrollment() 🆕
2. **central-g1f** (P2) - Backend: Exclude service accounts from isRoleMandatoryForTotp() 🆕
3. **central-ins** (P2) - Frontend: Update login component for enrollment flags
4. **central-fyl** (P2) - Frontend: Create optional enrollment prompt modal
5. **central-nbb** (P2) - Frontend: Create system settings UI for mandatory roles

### Priority 2: Other Work (7 tasks)

6. central-905 (P3) - Frontend E2E tests for 2FA flow
7. central-94t (P2) - Test: Dev + selfsign + None (PostgreSQL)
8. central-4km (P2) - Test: Dev + selfsign + Garage
9. central-2g2 (P2) - Test: Dev + upstream + None (PostgreSQL)
10. central-3ii (P2) - Test: Dev + upstream + Garage
11. central-ndz (P2) - Test: Prod + letsencrypt + None (PostgreSQL)
12. central-5sm (P2) - Test: Prod + letsencrypt + Garage

---

## Recommended Work Order

### Phase 1: Service Account Backend (2 tasks, ~1-2 hours)
```
1. central-7oo - Update shouldPromptEnrollment()
   └── Add is_service_account check, return false for service accounts

2. central-g1f - Update isRoleMandatoryForTotp()
   └── Add is_service_account check, return false for service accounts
```

**Note:** These tasks assume `users.is_service_account` column exists. If not:
- Make code backwards-compatible (treat null/undefined as false)
- Document that full functionality requires service account migration

### Phase 2: Frontend Components (3 tasks, ~4-6 hours)
```
3. central-ins - Update login component
   └── Capture requireTotpSetup and shouldPromptTotpEnrollment flags

4. central-fyl - Create optional enrollment prompt modal
   └── Modal with "Set Up Now", "Remind Later", "Don't Ask" buttons

5. central-nbb - Create system settings UI
   └── Admin UI to configure mandatory roles
```

### Phase 3: Frontend Integration (2 tasks, ~2-4 hours)
```
6. central-vdl - Create mandatory enrollment modal
   └── Non-dismissible modal for forced setup

7. central-iso - Integrate modals in home component
   └── Show appropriate modal based on flags
```

### Phase 4: Testing (2 tasks, ~2-3 hours)
```
8. central-b5k - Test service account exclusions
   └── Integration tests for service account behavior

9. central-5w2 - Full enrollment flow testing
   └── Integration tests for all scenarios
```

### Phase 5: Documentation (2 tasks, ~1-2 hours)
```
10. central-mox - Document service account exclusions
    └── Update plan and route docs

11. central-tbg - Update VG docs
    └── Complete enrollment feature documentation
```

**Total Estimated Time:** 10-18 hours (1-2 days)

---

## Critical Notes

### Service Account Column Dependency

The new tasks (central-7oo, central-g1f) check `users.is_service_account` column. This column:
- ✅ Will be added in service account security plan (future work)
- ⚠️ **Doesn't exist yet** in current database

**Solutions:**

**Option 1: Backwards-Compatible Code (Recommended)**
```javascript
// Handle missing column gracefully
if (user.is_service_account === true) {
  return false;  // Exclude service account
}
// Otherwise continue with normal logic
```

**Option 2: Add Placeholder Migration Now**
```sql
-- Quick migration to add column with default false
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS is_service_account BOOLEAN NOT NULL DEFAULT false;
```

**Option 3: Skip New Tasks Until Service Account Work**
- Complete original 13 enrollment tasks first
- Add service account exclusions later when column exists

**Recommendation:** Use Option 1 (backwards-compatible code) for now. Document that full functionality requires the service account column, but the code won't break if it's missing.

---

## Success Criteria

### Enrollment System (Original)
- ✅ Backend: Enrollment logic complete (5 tasks closed)
- 🔄 Frontend: Components being built (3 ready, 4 blocked)
- 🔄 Testing: Integration tests (2 blocked)
- 🔄 Docs: Feature documentation (2 blocked)

### Service Account Support (NEW)
- 🔄 Backend: Exclusion logic (2 ready)
- ⏳ Testing: Service account scenarios (1 blocked)
- ⏳ Docs: Exclusion documentation (1 blocked)

---

## Next Steps

**Immediate:**
1. Start with **central-7oo** - Update shouldPromptEnrollment()
   - Implement backwards-compatible check
   - Add comments about service account column requirement

2. Continue with **central-g1f** - Update isRoleMandatoryForTotp()
   - Same backwards-compatible approach

3. Move to **frontend work** (3 tasks ready)

**After Enrollment Complete:**
- Begin service account security work (25 new tasks)
- Full service account flag implementation
- API token management
- Testing and documentation

---

## Files Modified Summary

### Backend
- `server/lib/model/query/vg-web-user-totp.js` (2 methods updated)
- `server/lib/resources/sessions.js` (already modified)
- `server/lib/resources/vg-web-user-totp.js` (already modified)
- `server/lib/resources/vg-settings.js` (already modified)

### Frontend
- `client/src/components/account/login.vue` (capture flags)
- `client/src/components/home.vue` (show modals)
- `client/src/components/vg/vg-totp-enrollment-prompt-modal.vue` (NEW)
- `client/src/components/vg/vg-totp-mandatory-setup-modal.vue` (NEW)
- `client/src/components/system/vg-totp-settings.vue` (NEW)

### Tests
- `server/test/integration/api/vg-totp-enrollment.js` (add service account tests)

### Documentation
- `plan/2Fa-Enrollment-Flow.md` (add service account section)
- `docs/vg/vg-server/routes/web-user-totp.md` (update matrix)
- `docs/vg/vg-server/authentication-flows.md` (update diagrams)

---

## Conclusion

**Status:** ✅ Ready to proceed with enrollment work

**Progress:** 5 of 17 tasks complete (29%), 12 tasks ready (71%)

**Next Action:** Start with central-7oo (service account exclusion in shouldPromptEnrollment)

**Estimated Completion:** 1-2 days for all enrollment work
