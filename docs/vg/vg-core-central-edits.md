# VG core Central meta-repository edits

**Updated:** 2026-09-17
**Baseline:** upstream `getodk/central` tag `v2026.3.0`

This is the authoritative inventory of VG changes to upstream-existing files. New VG-owned files live in `docs/vg/`, `files/vg-nginx/`, `crs_custom/`, the Compose override files, and the numbered NGINX hooks. An upstream merge is incomplete until this ledger agrees with `git diff v2026.3.0`.

## Upstream-pure files

The following files must remain byte-identical to upstream `v2026.3.0`:

- `docker-compose.yml`
- `docs/news.html`
- `enketo.dockerfile`
- `files/enketo/config.json.template`
- `files/nginx/setup-odk.sh` (tracked but unused by the VG image)
- `postgres14.dockerfile`
- `secrets.dockerfile`
- `service.dockerfile`

This preserves upstream frontend, mail, Redis, Enketo, PostgreSQL, and Node version pins. VG behavior is layered through `docker-compose.override.yml`, `docker-compose.vg-dev.yml`, and `docker-compose.vg-prod.yml`.

## Required production seams

- `.env.template`: documents VG deployment variables, including branding and local development ports.
- `.gitmodules`: points client/server at the VG forks and registers the CRS and knowledge submodules.
- `Makefile`: adds VG dev/production Compose entry points and `check-compose-env`.
- `nginx.dockerfile`: retains the upstream Node 24.20.0 build stage while replacing only the runtime stage with the pinned VG WAF base and numbered Jonas-entrypoint hooks.
- `files/nginx/odk.conf.template`: uses the derived certificate path, trusted chain, spoof-resistant `X-Forwarded-For`, streaming response behavior, and VG WAF policy.
- `files/prebuild/write-version.sh`: reports the checked-out client revision for source/test builds so `/version.txt` reflects the release inputs.
- `.github/workflows/main.yml`: runs Compose environment parity and the VG NGINX/WAF validation.

## Repository and release support

`.dockerignore`, `.gitignore`, the GitHub issue/PR templates, and the deleted legacy `CHANGELOG.md` adapt repository hygiene and release workflow for the fork. `test/check-for-large-files.sh` and `test/check-scripts.sh` cover the added VG paths and scripts.

## NGINX test seam

The upstream NGINX harness is extended to exercise the WAF base, development HMR behavior, OData/API CRS exclusions, generated `/version.txt`, certificate modes, and cold-start readiness. The directly edited upstream files are:

```text
test/nginx/lib.docker-compose.yml
test/nginx/lint-config.sh
test/nginx/mock-http-server/index.js
test/nginx/mock-http-server/package-lock.json
test/nginx/mock-http-service.dockerfile
test/nginx/mock-sentry.dockerfile
test/nginx/mock-sentry/index.js
test/nginx/mock-sentry/package-lock.json
test/nginx/nginx.test.docker-compose.yml
test/nginx/src/lib.js
test/nginx/src/mocha/nginx.spec.js
test/nginx/src/mocha/setup-odk.spec.js
test/nginx/src/playwright/csp.spec.js
test/package-lock.json
test/package.json
```

The setup tests recreate only their target container with `--no-deps` and poll the externally observable HTTPS endpoint. This avoids shared dependency races during certificate generation.

## Exact upstream-file inventory

Every upstream-existing file that differs from `v2026.3.0` is listed below. Submodule pointer changes are included.

```text
.dockerignore
.env.template
.github/ISSUE_TEMPLATE/patch_release.md
.github/ISSUE_TEMPLATE/release.md
.github/PULL_REQUEST_TEMPLATE.md
.github/workflows/main.yml
.gitignore
.gitmodules
CHANGELOG.md (deleted)
Makefile
files/nginx/odk.conf.template
files/prebuild/write-version.sh
nginx.dockerfile
server (VG fork pointer)
client (VG fork pointer)
test/check-for-large-files.sh
test/check-scripts.sh
test/nginx/lib.docker-compose.yml
test/nginx/lint-config.sh
test/nginx/mock-http-server/index.js
test/nginx/mock-http-server/package-lock.json
test/nginx/mock-http-service.dockerfile
test/nginx/mock-sentry.dockerfile
test/nginx/mock-sentry/index.js
test/nginx/mock-sentry/package-lock.json
test/nginx/nginx.test.docker-compose.yml
test/nginx/src/lib.js
test/nginx/src/mocha/nginx.spec.js
test/nginx/src/mocha/setup-odk.spec.js
test/nginx/src/playwright/csp.spec.js
test/package-lock.json
test/package.json
```

Generic infrastructure filenames follow upstream conventions; VG-specific runtime files and configurations use `vg-`, `vg_`, `crs_custom`, or the documented numbered NGINX-hook convention.

## Upgrade checks

```bash
git diff --exit-code v2026.3.0 -- docker-compose.yml \
  docs/news.html enketo.dockerfile files/enketo/config.json.template \
  files/nginx/setup-odk.sh postgres14.dockerfile secrets.dockerfile service.dockerfile
make check-compose-env
docker compose -f docker-compose.yml -f docker-compose.override.yml config >/dev/null
npm --prefix test test
```

Record the final local and GitHub Actions results in the release changelog.
