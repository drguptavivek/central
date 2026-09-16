# VG Changelog: Upstream ODK Central v2026.2.4 Migration

**Date:** 2026-09-17

## Branches

- `central`: `merge-2026.2.4-clean`
- `client`: `merge-2026.2.4`
- `server`: `merge-2026.2.2`

## Included changes

- Central and client merged upstream `v2026.2.4`.
- Server merged the latest available upstream backend tag, `v2026.2.2`;
  upstream has no backend `v2026.2.4` tag.
- Upstream actor properties and dataset filtering are retained alongside VG
  app-user authentication, telemetry, and Data Manager authorization.
- The new `apps/central` frontend layout and mode-based build flow are used.
- VG ModSecurity/CRS and headers-more integration remains enabled in the
  production nginx template.
- NGINX now preserves the Jonas entrypoint/template contract without the old
  `setup-odk.sh`. ODK's `letsencrypt`, `selfsign`, `customssl`, and `upstream`
  modes are mapped explicitly; local development uses `SSL_TYPE=selfsign`,
  while public LetsEncrypt mode no longer defaults to the local CA.
- NGINX startup waits for the API and Enketo DNS names, and health verifies the
  generated ODK vhost rather than only Jonas's base HTTP listener.
- Backend runtime configuration is generated from the upstream
  `files/service/config.json.template` and Compose environment contract. The
  accidentally reintroduced tracked `server/config/local.json` and
  `server/config/test.json` files were removed because they overrode upstream
  test URLs, cookie behavior, and mail settings.
- Submission exports now require the explicit `submission.export` verb on
  every CSV, ZIP, and OData surface. Built-in Administrators and Project
  Managers retain export access; Project Viewers and Data Managers do not.
- The Compose override environment is checked against upstream in CI with
  `make check-compose-env`, preventing new upstream nginx keys from being
  silently dropped by the `!override` block.

## Upgrade and operations notes

- Existing app-user sessions with a `NULL` expiry are hard-invalidated during
  upgrade. Offline telemetry attempts made with those sessions receive 401 and
  are not stored; app users must sign in again.
- Weak-password validation now returns problem code `400.44` instead of
  `400.20`. Clients that branch on the old code must be updated.
- WAF anomaly-score blocking is live on `/v1/`. Monitor ModSecurity audit logs
  after deployment, especially for false positives on `PATCH` requests.
- Backend test runners must supply the required `PG*` environment variables.
- Docker Compose 2.24 or newer is required because the VG nginx override uses
  the `!override` tag.

## Submodule pointers

- `client` -> `c8e2b12b`
- `server` -> `e5314b68`
