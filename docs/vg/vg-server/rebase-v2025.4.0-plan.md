# Server Rebase Plan: v2024.3.1 → v2025.4.0

**Epic:** central-xav | **GitHub:** https://github.com/drguptavivek/central/issues/98
**Parent:** central-m56 | **GitHub:** https://github.com/drguptavivek/central/issues/97

## Overview

Rebase VG server fork from v2024.3.1 to upstream v2025.4.0.

### Scope
- **Upstream commits:** 274 commits to integrate
- **VG commits:** 358 commits to preserve
- **Risk level:** HIGH - Major conflicts in session management, auth, app-users
- **Estimated effort:** 3-5 sessions

### Key Conflicts Expected

1. **Session Management** (HIGH RISK)
   - Upstream PR #1586: config-based session lifetime for Web users
   - VG: Custom TTL logic for App users
   - Resolution: Keep both, ensure isolation

2. **Auth/Password** (MEDIUM RISK)
   - Upstream: Standardized password validation, 72-byte bcrypt limit
   - VG: Custom vg-password.js with complexity requirements
   - Resolution: Layer VG on top of upstream

3. **App-Users Endpoints** (MEDIUM RISK)
   - Upstream: Added attachment upload via REST
   - VG: Added login, password reset/change, revoke, activate endpoints
   - Resolution: Merge both sets of endpoints

4. **Database Migrations** (MEDIUM RISK)
   - Upstream: 33 new knex migrations
   - VG: Manual SQL migrations
   - Resolution: Run both, verify no conflicts

## Plan Structure

### Phase 0: Preparation (2 tasks)
Ready to start immediately:
- **P0.1:** Create backup branch vg-work-pre-rebase-2025.4.0
- **P0.2:** Document current VG server state

### Phase 1: Pre-Rebase Analysis (4 tasks)
Must complete before rebase starts:
- **P1.1:** Analyze session management conflicts (PR #1586)
- **P1.2:** Analyze auth/password conflicts  
- **P1.3:** Analyze database migration conflicts
- **P1.4:** Create comprehensive conflict resolution plan
  - **BLOCKS ALL PHASE 2 TASKS**

### Phase 2: Rebase Execution (6 tasks)
Sequential conflict resolution:
- **P2.1:** Start interactive rebase onto upstream/master
- **P2.2:** Resolve session management conflicts
- **P2.3:** Resolve auth/password conflicts
- **P2.4:** Resolve app-users endpoint conflicts
- **P2.5:** Resolve migration conflicts
- **P2.6:** Resolve remaining conflicts and complete rebase
  - Depends on P2.2-P2.5
  - **BLOCKS ALL PHASE 3 TASKS**

### Phase 3: Testing (5 tasks)
Comprehensive validation (can run in parallel):
- **P3.1:** Apply VG database schema and run migrations
  - **BLOCKS P3.2-P3.5**
- **P3.2:** Run VG unit tests
- **P3.3:** Run VG integration tests
- **P3.4:** Manual testing of VG features
- **P3.5:** Run full upstream test suite

### Phase 4: Finalization (5 tasks)
Push and integrate:
- **P4.1:** Update VG server documentation
  - Depends on all P3 tasks
- **P4.2:** Push rebased server to remote (force-push)
- **P4.3:** Update central meta repo submodule pointer
- **P4.4:** Update central meta repo to v2025.4.1
- **P4.5:** Final integration testing and closeout

## Dependency Chain

```
P0.1, P0.2 (parallel, no deps)
    ↓
P1.1, P1.2, P1.3 (parallel, can start when P0 done)
    ↓
P1.4 (depends on P1.1-P1.3)
    ↓
P2.1 (start rebase)
    ↓
P2.2, P2.3, P2.4, P2.5 (parallel conflict resolution)
    ↓
P2.6 (complete rebase)
    ↓
P3.1 (apply schema)
    ↓
P3.2, P3.3, P3.4, P3.5 (parallel testing)
    ↓
P4.1 (update docs)
    ↓
P4.2 → P4.3 → P4.4 → P4.5 (sequential finalization)
```

## Critical Success Factors

1. **DO NOT** skip or squash VG commits during rebase
2. **DO** create backup branch before starting
3. **DO** complete P1.4 conflict plan before P2.1 rebase
4. **DO** run all tests (P3.2-P3.5) before pushing
5. **DO** use --force-with-lease when pushing (P4.2)

## Rollback Plan

If critical issues found:
```bash
cd server
git reset --hard vg-work-pre-rebase-2025.4.0
git push --force-with-lease origin vg-work
```

## Commands

### View Epic
```bash
bd show central-xav
```

### See Ready Tasks
```bash
bd ready | grep central-xav
```

### Start First Task
```bash
bd update central-xav.1 --status=in_progress
```

### Track Progress
```bash
bd list --parent=central-xav --status=open
bd blocked | grep central-xav
```

## Files to Watch

High conflict probability:
- `lib/model/query/sessions.js`
- `lib/model/query/auth.js`
- `lib/resources/app-users.js`
- `lib/resources/sessions.js`
- `test/integration/api/vg-app-user-auth.js`
- `test/integration/api/sessions.js`

## Testing Checklist

After rebase, verify:
- [ ] App user login/logout flows
- [ ] Session TTL/cap enforcement
- [ ] Password reset/change
- [ ] QR code generation
- [ ] Login attempt tracking/lockouts
- [ ] Enketo Status page
- [ ] System Settings UI
- [ ] Project settings overrides
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No regressions in upstream features

## Resources

- Upstream release: https://github.com/getodk/central/releases/tag/v2025.4.1
- Server upstream: https://github.com/getodk/central-backend
- VG server fork: https://github.com/drguptavivek/central-backend
- Beads epic: central-xav (22 subtasks)
- GitHub epic: https://github.com/drguptavivek/central/issues/98

---

**Last Updated:** 2026-01-12
**Status:** Ready to begin Phase 0
