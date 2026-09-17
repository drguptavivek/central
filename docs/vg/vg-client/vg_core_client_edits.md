# VG core client edits

Current comparison baseline: upstream `central-frontend` tag `v2026.3.0`.

This is the authoritative inventory of edits to upstream-existing client files. VG-owned `vg-*` files are listed separately. An upstream merge is not complete until this inventory agrees with the tag-relative diff.

## Required production seams

### Route and navigation registration

Files:

- `apps/central/src/routes.js`
- `apps/central/src/util/load-async.js`
- `apps/central/src/components/project/show.vue`
- `apps/central/src/components/system/home.vue`

Change: register the VG App User Settings, Telemetry, Login History, System Settings, and Enketo Status routes and loaders; route the upstream `FieldKeyList` name to the VG App User list; expose the corresponding project/system tabs; use the narrow Data Manager form-access guard.

Reason: these are upstream registries and tab containers. A new VG component cannot become routable without a small registration seam here.

Risk/merge note: route names, loader names, permission guards, and visible tabs must remain synchronized. Preserve every upstream route from `v2026.3.0`; layer only the VG entries.

### Secure App User and Data Manager presentation

Files:

- `apps/central/src/components/project/form-access.vue`
- `apps/central/src/components/project/user/list.vue`
- `apps/central/src/request-data/project.js`
- `apps/central/src/request-data/resources.js`
- `apps/central/src/util/request.js`

Change: save Form Access through the VG project-scoped endpoint; show the Data Manager role; treat `active` rather than a returned token as the App User availability signal; register VG settings/status resources and `data_mgr`; add the Form Access API path.

Reason: VG intentionally does not return long-lived App User tokens. Data Manager has a narrower authorization contract than upstream Manager/Viewer roles, so the upstream token and project-update assumptions are not valid for this fork.

Risk/merge note: this is an authorization-sensitive seam. Data Manager must manage App Users/Form Access/submissions without gaining Connect Data or export/download rights. Viewer behavior must remain upstream-compatible.

### Web-user authentication feedback and inactivity policy

Files:

- `apps/central/src/components/account/login.vue`
- `apps/central/src/util/session.js`

Change: render attempts-remaining and retry-after feedback returned by hardened web login; invoke the VG inactivity helper from the upstream session lifecycle and clear/reset its cross-tab activity state at logout/login.

Reason: the HTTP session lifecycle is upstream core, while the policy implementation remains isolated in `vg-session-inactivity.js`.

Risk/merge note: preserve upstream login redirects, OIDC behavior, session-expiry handling, and storage-event logout behavior.

### Branding

Files:

- `apps/central/src/assets/scss/_variables.scss`
- `apps/central/src/components/navbar.vue`

Change: import VG color overrides last, use the accent variable for the active navbar state, and derive the brand label from `VITE_APP_NAME` with `ODK Central` as fallback.

Reason: allow deployment branding without duplicating the upstream navbar.

Risk/merge note: cosmetic only; the fallback must stay intact.

### Shared English source and generated Transifex catalog

Files:

- `apps/central/src/locales/en.json5`
- `apps/central/transifex/strings_en.json`

Change: add shared VG tab labels, Data Manager role name, and common unknown/not-available/login-lockout strings. The Transifex catalog is regenerated from the source messages.

Reason: route titles and shared role labels are outside individual VG component scopes.

Risk/merge note: do not copy English into non-English locale files. Missing translations fall back to English until translated. `npm run transifex:lint` must pass.

### Docker Vite host contract

File: `vite.config.js`

Change: bind Vite to `0.0.0.0` in the dev container and allow the public host from `DOMAIN` plus the internal Compose service name `client`. Upstream proxy paths remain intact.

Reason: different deployments use different `.env` domains, and the outer Central NGINX service reaches Vite over the Compose network.

Risk/merge note: never hard-code `central.local` here. Production routing remains NGINX-owned.

## Upstream-existing test and automation support

Files:

- `apps/central/test/data/field-keys.js`
- `apps/central/test/data/seed.js`
- `apps/central/test/index.js`
- `apps/central/test/util/http/data.js`
- `apps/central/karma.conf.js`
- `.github/workflows/tests.yml`
- `apps/central/docs/CONTRIBUTING.md`
- `e2e-tests/run-tests.sh`
- `bin/check-bundle-size.js`

Change: model `active` in App User fixtures, seed Data Manager and the narrow VG verb, install exact-signature expected-failure handling outside upstream test bodies, map HTTP fixtures to the VG list component, use a CI-safe Chrome launcher, provide the integration database environment in CI, retain the fork's local E2E domain default, and track the upstream OpenLayers `Vector.js` feature chunk with a 350 kB ceiling.

Reason: exercise the changed secure contract without rewriting upstream scenarios. Expected failures are exact-title and exact-message matched and fail on unexpected pass.

Risk/merge note: upstream test bodies must remain byte-identical to `v2026.3.0`. Only shared fixture/bootstrap adapters and VG-owned tests may differ.

## VG-owned files, not upstream core edits

The `apps/central/src/components/**/vg-*.vue`, `apps/central/src/util/vg-*.js`, `_vg_colors.scss`, VG tests, expected-failure helper, `Dockerfile.dev`, `start-dev.sh`, and the `custom-properties/vg-*.vue` components are fork-owned modules. Docker startup invokes Vite directly; the root upstream `package.json` dev script is unchanged.

## Removed historical core edits

The final `v2026.3.0` comparison contains no VG changes to `toast.vue`, `dataset/show.vue`, Form Attachment components, `form/head.vue`, `home/summary.vue`, `util/i18n.js`, `util/csv.js`, the root `package.json`, or `packages/xpath/vite.config.ts`. Earlier `$tc` modernization, whitespace-only edits, and macOS timezone changes were removed as unrelated to VG behavior.

## Exact upstream-file inventory

The following upstream-existing files differ from `v2026.3.0`. This list is the mechanical review checklist for every upgrade; no upstream edit may exist outside it without updating this ledger.

```text
.github/actions/restore-node/action.yml
.github/workflows/tests.yml
.nginx/.gitkeep (deleted; obsolete placeholder)
README.md
apps/central/docs/CONTRIBUTING.md
apps/central/karma.conf.js
apps/central/src/assets/scss/_variables.scss
apps/central/src/components/account/login.vue
apps/central/src/components/navbar.vue
apps/central/src/components/project/form-access.vue
apps/central/src/components/project/show.vue
apps/central/src/components/project/user/list.vue
apps/central/src/components/system/home.vue
apps/central/src/locales/en.json5
apps/central/src/request-data/project.js
apps/central/src/request-data/resources.js
apps/central/src/routes.js
apps/central/src/util/load-async.js
apps/central/src/util/request.js
apps/central/src/util/session.js
apps/central/test/components/field-key/list.spec.js
apps/central/test/components/field-key/new.spec.js
apps/central/test/components/navbar.spec.js
apps/central/test/components/project/show.spec.js
apps/central/test/data/field-keys.js
apps/central/test/data/seed.js
apps/central/test/index.js
apps/central/test/util/http/data.js
apps/central/transifex/strings_en.json
apps/forms/test/utils/api.spec.ts
bin/check-bundle-size.js
e2e-tests/run-tests.sh
vite.config.js
packages/xforms-engine/src/instance/attachments/buildAttributes.ts (deleted unused duplicate; active imports use instance/buildAttributes.ts)
```

`restore-node/action.yml` corrects the upstream cache glob typo (`package/*` to `packages/*`). The field-key/navbar/project tests and Forms API test adapt upstream assertions to the VG contract or carry upstream fixes. README and CONTRIBUTING describe the fork development contract. Each remaining path is covered by the functional groups above.

Fork-owned additions use `vg-`/`vg_` for runtime components and helpers. Generic build files and exact-signature test adapters retain conventional names. The retained Custom Properties views are fork-owned because upstream v2026.3.0 removed them; they are therefore named `vg-list.vue` and `vg-new.vue`.

## Validation

- Run full monorepo lint, including Transifex and formatting, for every release.
- Run the production web build, typecheck, and focused Vue tests for every release.
- Full Central browser suite must use Playwright's bundled Chromium, not system Google Chrome; record the final count in the release changelog and CI run.
