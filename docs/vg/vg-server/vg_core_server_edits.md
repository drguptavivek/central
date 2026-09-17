# VG core server edits

Current comparison baseline: upstream `central-backend` tag `v2026.3.0`.

This is the authoritative inventory of edits to upstream-existing server files. VG-owned modules and migrations are listed separately. An upstream merge is not complete until this inventory agrees with the tag-relative diff.

## Required production seams

### Request transaction and error-header handling

File: `lib/http/endpoint.js`

Change: treat only `POST /sessions` as non-transactional after API-version path rewriting, so failed-login audit/lockout writes survive the intentional 401; emit `Retry-After` and `X-Login-Attempts-Remaining` from Problem metadata.

Reason: the normal endpoint wrapper rolls back all writes when authentication rejects. VG rate limiting requires failed attempts to persist.

Risk/merge note: high authentication surface. The path match is exact and POST-only. Other write endpoints keep upstream transaction behavior.

### VG resource and query registration

Files:

- `lib/http/service.js`
- `lib/model/container.js`

Change: register namespaced VG resources and injected query modules. Literal routes such as `settings` and `telemetry` are registered before upstream `/app-users/:id` so they cannot be parsed as integer IDs.

Reason: upstream service/container files are the application registries.

Risk/merge note: preserve upstream registration order except for the required literal-before-parameter ordering.

### Secure App User API seam

Files:

- `lib/resources/app-users.js`
- `lib/model/query/field-keys.js`
- `lib/model/query/sessions.js`

Change: delegate create/update/presentation to the VG domain; create App Users without the upstream 9999-year session; redact session tokens; expose username/phone/active metadata; select only the newest session for compatibility metadata; require an active `vg_field_key_auth` row and a non-deleted actor when authenticating field-key bearers. Deletion deactivates VG credentials before the upstream actor deletion/session termination.

Reason: VG App Users authenticate with username/password and short-lived bearer sessions. Legacy field keys lacking VG auth must fail closed.

Risk/merge note: high authentication surface. Sessionless creation still writes `projectId`; deletion remains project-scoped and fail-closed for both new logins and existing bearer tokens; upstream non-VG actor/session behavior is preserved.

### Web-user login and password-reset hardening

Files:

- `lib/resources/sessions.js`
- `lib/resources/users.js`
- `lib/model/query/audits.js`
- `lib/util/problem.js`

Change: delegate login/reset initiation to VG domains, include VG login failure/lockout actions in the upstream user audit category, and define the password-policy Problem.

Reason: centralize timing-safe password checks, IP/email lockout, audit logging, reset throttling, and response metadata in VG modules while keeping the upstream routes stable.

Risk/merge note: preserve OIDC routing, current-session restore/delete, reset verification, and generic authentication error wording.

### App User project metadata

File: `lib/resources/projects.js`

Change: allow an authenticated VG App User to retrieve only its own project metadata through a narrow domain check before the upstream web-user authorization path.

Reason: short-lived App User clients need project metadata but do not receive broad `project.read` permission.

Risk/merge note: fail closed unless the bearer actor is a field key belonging to the requested project.

### Submission export boundary

Files:

- `lib/resources/odata.js`
- `lib/resources/submissions.js`

Change: route OData and CSV/ZIP authorization through `vg-submission-export-auth.js`.

Reason: export is a separate authorization capability. Administrator and Project Manager have `submission.export`; Project Viewer and Data Manager do not. `submission.read` continues to allow Viewer list, detail, and attachment access but never substitutes for export permission. Custom roles must also hold the explicit export verb.

Risk/merge note: high authorization surface and an intentional divergence from upstream Viewer download behavior. Validate Administrator/Manager success and Viewer/Data Manager denial separately across published and draft CSV, ZIP, OData service, metadata, collection, and row endpoints. The unchanged upstream Viewer test is handled by an exact expected-failure entry so any broader failure still fails the suite.

Upgrade repair: the original `20260520-01-vg-data-manager-role` migration added `submission.export` to Viewer before its pre-release definition was corrected. Migration `20260917-01-vg-reconcile-submission-export-verbs` is append-only and makes upgraded databases match fresh installations by ensuring the verb is present for Administrator/Manager and absent for Viewer/Data Manager without changing unrelated verbs.

### Legacy submission-event upgrade repair

Files:

- `lib/model/migrations/20260115-01-submission-event-stamping-unshared-events-01.up.sql`
- `lib/model/migrations/20260115-01-submission-event-stamping-unshared-events-02.up.sql`
- `lib/model/migrations/20260115-01-submission-event-stamping-unshared-events-03.up.sql`

Change: before renumbering legacy duplicate events, disable both submission event triggers; renumber deterministically; create the unique index only after renumbering; recreate `get_event()`; restore both triggers. Index drops/creates are retry-safe.

Reason: a later migration cannot help a database that fails while running this upstream migration. Legacy duplicate event values must be repaired before the unique index is created. Disabling only `set_eventstamp_submissions_at_commit` is insufficient because `blank_submissions_event_on_update` rewrites the assigned values to `NULL`.

Transaction decision: `20260115-01-submission-event-stamping-unshared-events.js` is now byte-identical to upstream and does **not** export `config: { transaction: false }`. The flag was introduced when the repair was split into disable/renumber, index, and recreate/enable phases, apparently to commit those phases separately around the deferred trigger. That is unnecessary here: trigger enablement changes take effect inside the migration transaction, and the migration uses ordinary `CREATE INDEX`, not a command such as `CREATE INDEX CONCURRENTLY` that PostgreSQL forbids in a transaction. The normal Knex transaction therefore keeps the trigger/data/index/function changes atomic and avoids leaving a half-applied schema if a later phase fails. The actual `NULL` bug was caused by failing to disable `blank_submissions_event_on_update`, not by transaction scope.

Risk/merge note: changing an old migration is intentional only because it repairs the not-yet-run upgrade path. Databases that already recorded the flawed VG variant are repaired by the new append-only `20260902-01-vg-repair-null-submission-events` migration, which preserves valid event numbers and fills only missing values after the existing maximum.

## Test command seam

File: `Makefile`

Change: the normal integration target loads `test/vg/mocha-expected-failures.js`; a focused sessions target uses the same hook.

Reason: the hook supplies standard assertion extensions, a test-process-only legacy fixture adapter, and exact-title/exact-message xfail handling for the eight upstream scenarios that intentionally assert the removed permanent-token contract.

Risk/merge note: this is not a blanket skip. Unknown failures and unexpected passes fail the run. Upstream test bodies remain byte-identical to `v2026.3.0`.

## VG-owned files, not upstream core edits

Namespaced domain/query/resource modules, `vg-password.js`, `vg-submission-export-auth.js`, VG auth/Data Manager/role-normalization/repair migrations, VG integration/unit/migration tests, and `test/vg/**` are fork-owned. Session trimming and display-name updates were moved into VG query modules; `lib/model/query/actors.js` and `lib/model/query/users.js` no longer carry VG edits.

## Removed historical core and local-config edits

- `config/local.json` and `config/test.json` are not tracked. Runtime config is
  generated from Central's upstream template and Compose environment; test
  database values are supplied explicitly by the test command. Tracking these
  files caused local domain, secure-cookie, and mail settings to leak into the
  upstream integration suite.
- `lib/model/query/actors.js`, `lib/model/query/users.js`, and the migration
  wrapper `20260115-01-submission-event-stamping-unshared-events.js` are
  byte-identical to upstream. VG behavior is kept in namespaced modules and SQL
  phase files.

## Exact upstream-file inventory

The following upstream-existing files differ from `v2026.3.0`. This is the mechanical upgrade checklist; every path must remain covered by the functional sections in this document.

```text
.github/workflows/oidc-integration.yml
.github/workflows/s3-e2e.yml
Makefile
README.md
config/s3-dev.json
docs/database.md
lib/bin/s3-create-bucket.js
lib/http/endpoint.js
lib/http/service.js
lib/model/container.js
lib/model/migrations/20260115-01-submission-event-stamping-unshared-events-01.up.sql
lib/model/migrations/20260115-01-submission-event-stamping-unshared-events-02.up.sql
lib/model/query/audits.js
lib/model/query/field-keys.js
lib/model/query/sessions.js
lib/resources/app-users.js
lib/resources/odata.js
lib/resources/projects.js
lib/resources/sessions.js
lib/resources/submissions.js
lib/resources/users.js
lib/util/problem.js
test/bin/docker-postgres.sh
test/e2e/s3/run-tests.sh
test/e2e/s3/test.js
```

The OIDC workflow extends the timeout so always-run PostgreSQL diagnostics can finish. The S3 workflow, `config/s3-dev.json`, `lib/bin/s3-create-bucket.js`, and S3 test files replace the abandoned MinIO test service with digest-pinned Garage while retaining the S3-compatible Node client. `test/bin/docker-postgres.sh` polls readiness for up to 60 seconds instead of assuming a two-second cold start. README and database docs describe the fork contract.

## Naming exceptions

Runtime modules, new role/auth migrations, and their tests use `vg-` or `vg_`. `lib/model/migrations/20260115-01-submission-event-stamping-unshared-events-03.up.sql` is an unprefixed historical migration phase tied to upstream's numbered migration. It may already be recorded in deployed migration histories, so it is frozen as a compatibility exception; future fork migrations must use the VG prefix. `test/e2e/s3/garage.toml` follows the emulator product name, and the upstream-migration regression spec follows the migration name.

## Validation

- Database migration suite: 13 passing, zero failing, including duplicate-event renumbering and append-only `NULL` repair.
- Server unit suite: 1,347 passing, one upstream pending, zero failing.
- Server lint: pass on 2026-09-02.
- Record full integration and focused security counts in the release changelog and CI run; `GATES.md` is not tracked.
