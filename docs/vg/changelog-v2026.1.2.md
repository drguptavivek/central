# VG Changelog: Upstream ODK Central v2026.1.2 Migration

**Date:** 2026-06-08

## Summary

This migration updates the VG fork toward upstream ODK Central `v2026.1.2`.
The released upstream change is frontend-focused:

- `central` meta repo points at the upstream frontend `v2026.1.2` line.
- `client` merges upstream `central-frontend` `v2026.1.2`.
- `server` remains on the current VG backend line because upstream
  `central-backend` has no `v2026.1.2` release tag at migration time.

## Branches

- `client`: `upgrade/client-v2026.1.2`
- `central`: `upgrade/central-v2026.1.2`

## Upstream Changes

Included from upstream frontend `v2026.1.2`:

- Upgrade ODK Web Forms to `v0.24`.
- Fix PrimeVue 4 compatibility by installing Web Forms on the app instance.
- Add modern favicon and web manifest assets.
- Harden default npm configuration.
- Handle synthetic feature-flag key events without throwing.

Included from upstream Central meta repo `v2026.1.2`:

- Update the client submodule pointer for upstream frontend `v2026.1.2`.
- Update public Central news entries.

## Client Changes

The client branch merged upstream frontend `v2026.1.2` into the VG frontend
fork while preserving VG App User and Data Manager customizations.

Submodule state after client migration:

- `client` -> `7ed1a50ca2d8d8981b749737ab272bee831596c5`

## Server Changes

No server release tag exists for upstream backend `v2026.1.2` at migration
time. The VG backend remains on:

- `server` -> `2d5b1648e5e045a9faa39441a2f136b2fd1b7af4`

## Validation

Completed:

- `npm_config_cache=/private/tmp/central-client-npm-cache npm install` passed
  in `client/`.
- `npm run build` passed in `client/`.
- Focused Karma tests passed in `client/`:
  `TEST_PATTERN='useFeatureFlags|WebFormRenderer' npm test`.

Notes:

- The first `npm install` attempted to use `~/.npm` and failed because the
  cache contains root-owned files; using a temporary npm cache avoided changing
  home-directory permissions.
- The first focused Karma attempt used the wrong grep pattern and matched zero
  tests; the corrected pattern executed 20 tests successfully.
