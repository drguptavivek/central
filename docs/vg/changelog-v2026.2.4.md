# VG Changelog: Upstream ODK Central v2026.2.4 Migration

**Date:** 2026-09-01

## Branches

- `central`: `merge-2026.2.4`
- `client`: `merge-2026.2.4`
- `server`: `merge-2026.2.4`

## Included changes

- Central and client merged upstream `v2026.2.4`.
- Server merged the latest available upstream backend tag, `v2026.2.2`;
  upstream has no backend `v2026.2.4` tag.
- Upstream actor properties and dataset filtering are retained alongside VG
  app-user authentication, telemetry, and Data Manager authorization.
- The new `apps/central` frontend layout and mode-based build flow are used.
- VG ModSecurity/CRS and headers-more integration remains enabled in the
  production nginx template.

## Submodule pointers

- `client` -> `23659645`
- `server` -> `55c926de`
