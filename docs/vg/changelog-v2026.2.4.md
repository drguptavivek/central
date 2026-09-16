# VG Changelog: Upstream ODK Central v2026.2.4 Migration

**Date:** 2026-09-01

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

## Submodule pointers

- `client` -> `6cc736df`
- `server` -> `55c926de`

These are the pre-finalization submodule HEADs. Final pointers must be recorded
only after the client and server changes are fully validated and committed.
