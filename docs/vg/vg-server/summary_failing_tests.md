# Failing integration tests (grouped)

- **Total failures:** 172 (from full `test/integration/api` run, 1461 passing, 8 pending).

## Legacy app-user flow (38)
- Source: `test/integration/api/app-users.js`.
- Symptoms: 400s instead of expected 200s; transaction depth errors when hitting `users/current`.
- Status: superseded by our VG short-token/project-bound flow; covered by `vg-app-user-auth.js` and `vg-tests-orgAppUsers.js`.
- Next: mark legacy specs pending or rewrite to new flow; otherwise full suite will keep failing.
- Gaps vs VG suite (not currently covered): creation/list permissions (403 cases), project-manager create/delete paths, ordered listing with revoked/ended sessions handling, extended metadata/last-used fields, audit logging for delete, delete assignment cleanup and project scoping, and legacy long-session restore endpoint.

## Submissions API flow (≈60)
- Source: `test/integration/api/submissions.js`.
- Symptoms: 400/409/500 mismatches on edit/patch/delete/attachment and app-user submission cases; one base URL expectation mismatch (`https://central.local` vs `http://localhost:8989`).
- Coverage: partially mirrored in VG submission tests for short-token app users; core legacy expectations still failing.
- Next: decide whether to align behavior to legacy expectations, or update/skip those specs for the customized flow.

## User email/reset notifications (≈30)
- Source: `test/integration/api/users.js`.
- Symptoms: mail count assertions expect zero but see non-zero; 400 vs 200 for app-user `users/current`.
- Coverage: not exercised by VG app-user suite; needs investigation if email behavior changed intentionally.

## Other/uncategorized (remainder)
- A handful of other failures in the full run fall outside the above buckets; review `server/plan/failing _tests.md` for specifics once priorities above are resolved.

## Action summary
- Keep running targeted VG suites to validate our flow.
- Choose a strategy for legacy `app-users.js` (skip/port) to unblock full-suite green.
- Triage submissions and user-email discrepancies based on desired behavior in the customized deployment.
