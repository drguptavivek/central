# VG app-user auth: test scenarios and status

> **Last Updated**: 2026-01-13

Key scenarios covered for the vg app-user auth / short-lived token work.

Note: the test suite uses the fixture `server/test/integration/fixtures/03-vg-app-user-auth.js` to create VG tables in the test DB. It does not apply `server/docs/sql/vg_app_user_auth.sql` directly; that SQL file is for manual setup/upgrade in non-test environments.

## Test inventory (current)

Approximate test counts (by `it(...)` blocks):

- Integration:
  - `test/integration/api/vg-app-user-auth.js`: 55
  - `test/integration/api/vg-tests-orgAppUsers.js`: 22
  - `test/integration/api/vg-telemetry.js`: 13
  - `test/integration/api/vg-webusers.js`: 6
  - `test/integration/api/vg-web-user-ip-rate-limit.js`: 11
  - `test/integration/api/vg-web-user-lockout.js`: 16
  - `test/integration/api/vg-enketo-status.js`: 5
  - `test/integration/api/vg-enketo-status-domain.js`: 3
  - `test/integration/api/vg-enketo-status-api.js`: 6
- Unit:
  - `test/unit/util/vg-password.js`: 6
  - `test/unit/domain/vg-app-user-auth.js`: 1

Total (above files): 144

| Scenario | Coverage | Status | Notes | Command |
| --- | --- | --- | --- | --- |
| Create app user with no long-lived session; login issues short token + projectId; session TTL ≈ 3 days | `test/integration/api/vg-app-user-auth.js` | ✅ Pass | Verifies creation has no session, login returns token with ~72h expiry | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha --recursive test/integration/api/vg-app-user-auth.js` |
| Lockout policy and recovery | `test/integration/api/vg-app-user-auth.js` | ✅ Pass | 5 failed attempts → lock for ~10 minutes; lock lifts after window | same as above |
| Session caps (default 3, DB override 2) | `test/integration/api/vg-app-user-auth.js` | ✅ Pass | Fourth login prunes oldest; DB setting `vg_app_user_session_cap`=2 enforced | same as above |
| Audit logging across lifecycle | `test/integration/api/vg-app-user-auth.js` | ✅ Pass | Emits vg.app_user.* for create, login success/failure, password change/reset, revoke, deactivate | same as above |
| Password change/reset/deactivate behaviors | `test/integration/api/vg-app-user-auth.js` | ✅ Pass | Password change drops old sessions; admin reset + deactivate block login; deactivated token rejected | same as above |
| Username rules and RBAC guards | `test/integration/api/vg-app-user-auth.js` | ✅ Pass | Normalizes usernames, rejects duplicates/blank/invalid, enforces self-only ops and blocks user password routes | same as above |
| Expired token rejection | `test/integration/api/vg-app-user-auth.js` | ✅ Pass | Manually expired session cannot be used | same as above |
| Submission: happy path via /key/:token | `test/integration/api/vg-tests-orgAppUsers.js` | ✅ Pass | VG app-user login token allows assigned form submission | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-tests-orgAppUsers.js` |
| Submission denied after admin revoke | `test/integration/api/vg-tests-orgAppUsers.js` | ✅ Pass | Revoke-admin blocks subsequent submissions | same as above |
| Submission denied when deactivated | `test/integration/api/vg-tests-orgAppUsers.js` | ✅ Pass | Deactivated app-user token rejected | same as above |
| Submission denied for unassigned form | `test/integration/api/vg-tests-orgAppUsers.js` | ✅ Pass | No assignment → 403 on submit | same as above |
| Submission denied with expired/foreign/malformed tokens | `test/integration/api/vg-tests-orgAppUsers.js` | ✅ Pass | Covers expired token, token from another project, and malformed token cases | same as above |
| Submission with old token after password change fails; new token works | `test/integration/api/vg-tests-orgAppUsers.js` | ✅ Pass | Old token 403, new token 200 post-change | same as above |
| Telemetry capture + admin listing (filters, paging) | `test/integration/api/vg-telemetry.js` | ✅ Pass | App-user telemetry write and system admin listing with filters | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-telemetry.js` |
| Web-user login hardening (audit, lockout duration, attempts remaining, Retry-After) | `test/integration/api/vg-webusers.js` | ✅ Pass | Covers `/v1/sessions` behavior (non-OIDC): lockouts + headers + audit details | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-webusers.js` |
| IP-based rate limiting for web users (prevents username enumeration) | `test/integration/api/vg-web-user-ip-rate-limit.js` | ✅ Pass | 20 failed attempts per IP → lock 30 min; independent of per-user lockout; time window filtering; different IPs tracked separately | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-web-user-ip-rate-limit.js` |
| Per-user web lockout (email+IP based) | `test/integration/api/vg-web-user-lockout.js` | ✅ Pass | 5 failed attempts per email+IP → lock 10 min; case-insensitive email tracking; audit logging; missing IP handling; retry-after headers | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-web-user-lockout.js` |
| Enketo form status across all projects | `test/integration/api/vg-enketo-status.js` | ✅ Pass | Returns enketo status summary; counts by status type; filters by projectId; determines closed status correctly | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-enketo-status.js` |
| Enketo ID regeneration (domain) | `test/integration/api/vg-enketo-status-domain.js` | ✅ Pass | Regenerate enketoId for open forms; fail for closed/non-existent forms | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-enketo-status-domain.js` |
| Enketo status API endpoints (system) | `test/integration/api/vg-enketo-status-api.js` | ✅ Pass | GET /v1/system/enketo-status; POST /v1/system/enketo-status/regenerate; RBAC (config.read/config.set); filter by projectId/xmlFormId | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-enketo-status-api.js` |
| Unit: password policy accept | `test/unit/util/vg-password.js` | ✅ Pass | Valid password returns true | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/util/vg-password.js` |
| Unit: too short | `test/unit/util/vg-password.js` | ✅ Pass | Rejects short password | same as above |
| Unit: missing special char | `test/unit/util/vg-password.js` | ✅ Pass | Rejects missing special | same |
| Unit: missing uppercase | `test/unit/util/vg-password.js` | ✅ Pass | Rejects missing uppercase | same |
| Unit: missing lowercase | `test/unit/util/vg-password.js` | ✅ Pass | Rejects missing lowercase | same |
| Unit: missing digit | `test/unit/util/vg-password.js` | ✅ Pass | Rejects missing digit | same |
| Unit: self revoke requires current session | `test/unit/domain/vg-app-user-auth.js` | ✅ Pass | Ensures `revokeSessions(..., currentOnly=true)` rejects if current session missing | `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/domain/vg-app-user-auth.js` |

Run in this session:
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha --recursive test/integration/api/vg-app-user-auth.js`
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/util/vg-password.js`
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-tests-orgAppUsers.js` (vg-only rewrite of legacy app-user routes)
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-telemetry.js`
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-webusers.js`
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-web-user-ip-rate-limit.js` (IP rate limiting - prevents username enumeration)
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-web-user-lockout.js` (per-user web lockout)
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-enketo-status.js`
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-enketo-status-domain.js`
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-enketo-status-api.js`
- ✅ `NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/domain/vg-app-user-auth.js`
