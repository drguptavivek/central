# VG upstream sessions test exceptions

The checkout has no `test/integration/other/sessions.js`; the upstream suite is
`test/integration/api/sessions.js`. It is not modified by VG.

Run the suite through the opt-in VG target:

```bash
make test-integration-vg-sessions
```

The target loads `test/vg/mocha-expected-failures.js`, which first loads the
shared assertions and then applies the exact-title manifest in
`test/vg/expected-failures.json`.

VG-owned files are `test/vg/mocha-expected-failures.js` and
`test/vg/expected-failures.json`; the upstream sessions test remains
unchanged. The only upstream core edit for this wiring is the opt-in Makefile
target documented in `vg_core_server_edits.md`.

The unmodified suite reports 15 failures when run standalone:

1. `api: /sessions POST should return a new session if the information is valid`
2. `api: /sessions POST should return a new session even if invalid auth is passed in the header - invalid session cookie`
3. `api: /sessions POST should return a new session even if invalid auth is passed in the header - invalid bearer token`
4. `api: /sessions POST should return a new session even if invalid auth is passed in the header - invalid basic auth`
5. `api: /sessions POST should treat email addresses case insensitively`
6. `api: /sessions POST should provide a csrf token when the session returns`
7. `api: /sessions POST weird bcrypt implementation details should treat a password repeated once as the singular version of the same`
8. `api: /sessions POST weird bcrypt implementation details should treat a password repeated twice as the singular version of the same`
9. `api: /sessions POST weird bcrypt implementation details should treat a password repeated until truncation as the singular version of the same`
10. `api: /sessions /restore GET should return the active session if it exists`
11. `api: /sessions /:token DELETE should log the action in the audit log if it is a field key`
12. `api: /sessions /:token DELETE should allow managers to delete project app user sessions`
13. `api: /sessions /:token DELETE should not allow app users to delete their own sessions`
14. `api: /sessions /:token DELETE should log the action in the audit log for app users`
15. `api: /sessions /current DELETE should not allow app users to delete their own sessions`

Titles 1-10 are not VG expected failures. They are standalone-run assertion
loading failures (`Session`, `token`, or `eqlInAnyOrder` extensions missing),
and the VG root hook loads `test/assertions.js` so they execute normally.

Titles 11-15 are allowlisted. Each attempts to create an app user using
the upstream legacy payload and then reads `body.token`/`appUser.token` to
operate on the resulting long-lived field-key session. VG deliberately emits
no create/list/get field-key or session token; username/password login issues
the short-lived bearer instead. The hook executes these tests and turns only
the exact expected `expected 200 "OK", got 400 "Bad Request"` failure into a
pending test. A different failure is propagated normally. If an allowlisted
test passes, the hook fails the run (XPASS), and any title not present in the
manifest is never reclassified.

The same external manifest also contains three exact cases from the unmodified
upstream `test/integration/api/app-users.js` suite:

1. `api: /projects/:id/app-users POST should create a long session`
2. `api: /projects/:id/app-users POST should log the action in the audit log`
3. `api: /projects/:id/app-users /:id DELETE should log the action in the audit log`

For these cases the fixture adapter supplies valid VG credentials so each test
reaches its real assertion. They remain expected failures because VG uses a
short-lived login session and the namespaced `vg.app_user.create` audit action.
No upstream test body is edited. A mismatched failure or unexpected pass still
fails the run.

Validation on 2026-09-01:

- Unmodified standalone suite: 36 passing, 15 failing.
- With shared assertions loaded: 46 passing, 5 failing (the five listed
  secure-contract cases).
- VG target: 46 passing, 5 pending expected failures.
- Final blank-database integration run on 2026-09-02: 2690 passing,
  13 pending (eight exact VG contract xfails and five upstream pending), zero
  failing.
