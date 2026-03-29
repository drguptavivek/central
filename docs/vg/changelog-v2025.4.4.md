# VG Changelog: Upstream ODK Central v2025.4.4 Migration

**Date:** 2026-03-29

## Summary

This migration updates the VG fork to upstream ODK Central `v2025.4.4` for:

- `client`
- `central` (submodule pointer bump)

The `server` fork remains on the upstream `v2025.4.2` line. No VG server
rebase or release bump was performed as part of this migration.

## Branches

- `client`: `upgrade/client-v2025.4.4`
- `central`: `upgrade/central-v2025.4.4`

## Client Changes

The client branch merged upstream `v2025.4.4` into the VG fork and fixed
a bundle size regression uncovered by the upgrade.

### Upstream files updated

- `.github/workflows/tests.yml`
- `bin/check-bundle-size.js`
- `package.json` (`@getodk/web-forms` bumped `^0.21.0` → `^0.22.0`)
- `package-lock.json`
- `src/components/geojson-map.vue`

### Notable upstream effects

- `@getodk/web-forms` updated from `^0.21.0` to `^0.22.0`
- `GeojsonMap` now includes OpenLayers `Attribution` control (non-collapsible)
- Map zoom button repositioned from `bottom: $spacing` to `bottom: 35px`
- Attribution styling added to `.ol-attribution` in `geojson-map.vue`
- Bundle size thresholds updated in `check-bundle-size.js`

### VG-specific fixes in this migration

**Bundle size regression (CI failure)**

The v2025.4.4 upstream `check-bundle-size.js` reduced the general JS limit
to 200 KB. `vg-list.js` was 566 KB because it statically imported all
app-user modal components (`vg-new`, `vg-qr-panel`, `vg-reset-password`),
which pull in `qrcode-generator`, `pako`, and `@faker-js/faker`.

Fix: convert the three heavy modals to `defineAsyncComponent` via
`loadAsync()`, matching the pattern used for `WebFormRenderer` and
`AnalyticsIntroduction`. `vg-list.js` dropped from 566 KB to 42 KB.

Side effect: `Vector.js` (OpenLayers, 322 KB) and `password-generator.js`
(faker, 477 KB) became separate lazy chunks. Both have explicit special
cases added to `check-bundle-size.js` — they only load when a map or
admin modal is rendered.

Files changed:
- `src/components/field-key/vg-list.vue` — async imports for heavy modals
- `src/util/load-async.js` — added `VgFieldKeyNew`, `VgFieldKeyResetPassword`, `VgFieldKeyQrPanel`
- `bin/check-bundle-size.js` — added special cases for `Vector.js` and `password-generator.js`

### VG policy used for this migration

- Take upstream for `src/components/geojson-map.vue`
- Take upstream for `.github/workflows/tests.yml`
- Preserve all VG UI/routes/custom components outside the upstream delta

## Central Changes

The central branch updates the `client` submodule pointer to the migrated
client commit and writes this changelog.

Submodule state after migration:

- `client` → merged `upgrade/client-v2025.4.4` commit
- `server` remains on the existing VG server line (`v2025.4.2`)

## GitHub Releases

- `drguptavivek/central-frontend`: `v2025.4.4-vg.1`
- `drguptavivek/central`: `v2025.4.4-vg.1`

## Validation

Completed:

- `client`: merge completed cleanly (no conflicts)
- `client`: `npm run build` passed locally
- `client`: CI Build job passing
- `central`: submodule pointer updated cleanly

Not completed:

- No integrated Docker stack smoke test was run in this migration step
- No dedicated web-forms validation was performed, by design

## Known Pre-existing Test Failures

69 upstream Karma unit tests fail on `vg-work` and are unrelated to this
migration. They fall into two categories:

1. **App user / FieldKey tests** (~59): upstream tests for the old `list.vue`
   which VG replaced with `vg-list.vue`, and tests relying on `token` presence
   which VG changed to `active === true`.
2. **Date formatting tests** (~10): timezone-offset failures on macOS CI
   agent, unrelated to any code change.
