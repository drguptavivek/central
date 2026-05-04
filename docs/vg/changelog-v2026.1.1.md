# VG Changelog: Upstream ODK Central v2026.1.1 Migration

**Date:** 2026-05-04

## Summary

This migration updates the VG fork to upstream ODK Central `v2026.1.1` for:

- `server`
- `central` meta repo

The `client` fork remains on the existing VG client line because upstream
`central-frontend` did not publish a `v2026.1.1` tag at migration time.

## Branches

- `server`: `migration/v2026.1.1`
- `central`: `migration/v2026.1.1`

## Upstream Changes

Included from upstream Central `v2026.1.1`:

- Exclude deleted Entity properties from GeoJSON output.
- Remove duplicate `PGAPPNAME` from `docker-compose.yml`.
- Upgrade `pyxform-http` from `v4.4.0` to `v4.4.1`.
- Insert itemset declaration for range labels through the pyxform image bump.
- Update Content Security Policy reporting.
- Add modern favicon and web manifest handling to nginx/test fixtures.

## Server Changes

The server branch merged upstream backend `v2026.1.1` into the VG backend
fork and then merged that migration branch back into `vg-work`.

Notable files changed:

- `.npmrc`
- `lib/model/query/geo-extracts.js`
- `test/integration/api/datasets.js`
- `test/integration/api/geodata.js`

Submodule state after migration:

- `server` -> `5aa0e0b52c51a42f28d73ae61f618c86f9001dfa` (`v2026.1.1-vg.1`)
- `client` -> unchanged from the existing VG client pointer

## Central Changes

The central branch merged upstream `v2026.1.1` and preserved the VG minimal
fork override pattern.

Conflict policy used:

- `docker-compose.yml`: accepted upstream so the file remains pure upstream.
- `server`: resolved to the VG backend merge commit that already includes
  upstream backend `v2026.1.1`.
- `files/nginx/odk.conf.template`: accepted upstream CSP/reporting and modern
  favicon/webmanifest changes, then reapplied the VG ModSecurity and
  headers-more directives.
- `.gitmodules`, `docs/vg/`, CRS/modsecurity override files, and VG submodule
  URLs remain VG-owned.

## Validation

Completed:

- `git diff --check` passed after conflict resolution.
- Verified upstream `central` has tag `v2026.1.1`.
- Verified upstream `central-backend` has tag `v2026.1.1`.
- Verified upstream `central-frontend` has no `v2026.1.1` tag at migration time.
- Docker daemon was reachable, but no Central compose services were running.

Not completed:

- Server Mocha integration tests did not run locally because `server/node_modules`
  was empty and `npx` attempted a network package lookup.
- Docker-based server integration tests were not run because the compose stack
  was not running.

## Known Pre-existing Test Failures

The known VG client test failures from prior migrations remain out of scope:

1. App user / FieldKey tests for upstream `list.vue` behavior that VG replaced
   with `vg-list.vue`.
2. Date formatting tests affected by local timezone offset on macOS.
