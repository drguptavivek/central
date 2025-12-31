# VG Client Fork: Customizations vs Upstream

This document summarizes all frontend changes in the `vg-work` branch of the
forked Central client compared to the upstream ODK Central client.

## Comparison Baseline

- Upstream: `getodk/central-frontend` `upstream/master` at `101b2341b1b110791615caeb010f8821637649a0`
- Fork: `drguptavivek/central-frontend` `vg-work` at `c50d30213a1b691f0329a47e281bfd4aeee3865c`

## Summary of Customizations

1) App User auth overhaul (short-lived sessions, username/password flow, secure
   QR codes, additional fields like phone) across list/create/reset/edit flows.
2) Admin System Settings UI for App User session TTL, session cap, and admin_pw (Collect).
3) Dev environment and proxy changes for `central.local` and Dockerized Vite.
4) E2E test defaults and reliability tweaks.

---

## 1) App User Auth: UI + UX Changes

### Field Key list now uses VG components

- Loader now resolves `FieldKeyList` to `vg-list.vue` instead of `list.vue`.
  - `src/util/load-async.js`
- New list view adds **Username** and **Phone** columns, and new actions:
  edit details, reset password, revoke access, restore access.
  - `src/components/field-key/vg-list.vue`
  - `src/components/field-key/vg-row.vue`

### Create App User (VG flow)

- Creation uses a **generated password** (no manual password entry).
- Adds **Username** and **Phone** input fields with validation.
- After create, the modal shows username + password and a QR panel that excludes
  credentials (secure QR).
  - `src/components/field-key/vg-new.vue`
  - `src/util/password-generator.js`
  - `src/components/field-key/vg-qr-panel.vue`

### Reset Password

- Reset flow now **auto-generates** a new password and shows it to the admin.
- Uses a dedicated reset endpoint and shows updated credentials in the QR panel.
  - `src/components/field-key/vg-reset-password.vue`
  - `src/util/password-generator.js`

### Edit and Revocation

- New **Edit App User** modal supports changing display name and phone.
  - `src/components/field-key/vg-edit.vue`
- Revoke uses an admin revoke endpoint and marks access revoked.
  - `src/components/field-key/vg-revoke.vue`
- Restore access is a new modal that reactivates a user.
  - `src/components/field-key/vg-restore.vue`

### Secure QR behavior

- Managed QR code only includes server URL and project info.
- Includes `admin_pw` for ODK Collect settings configuration (project-level override, system default).
- Username/password are shown below the QR code but are NOT embedded.
  - `src/components/field-key/vg-qr-panel.vue`

### App Users in Form Access

- Form Access now lists **active** users even if tokens are short-lived and not
  returned in listings.
  - `src/request-data/project.js`

### API path additions

New request helpers added to support the new auth flow:
- `fieldKeyLogin`
- `fieldKeyUpdate`
- `fieldKeyResetPassword`
- `fieldKeyRevoke` (admin revoke)
- `fieldKeyActive` (restore/deactivate)
  - `src/util/request.js`

### UX and i18n updates

- New app-user settings label in System tabs.
- English strings for new system settings and validation message.
  - `src/components/system/home.vue`
  - `src/locales/en.json5`

---

## 2) System Settings UI for App User Sessions

Adds a new System tab to configure session policies for app users.

- New **System > App User Settings** tab.
  - `src/components/system/home.vue`
  - `src/routes.js`
- New settings view for TTL + max sessions (both must be >= 1) and `admin_pw`.
  - `src/components/system/vg-settings.vue`
- Data resource for `/v1/system/settings`.
  - `src/request-data/resources.js`
- Toast styling update to show success in green.
  - `src/components/toast.vue`
  - `src/container/alerts.js`

---

## 2.1) routes.js Changes (Detailed)

`src/routes.js` has two substantive functional changes and one large formatting
change:

1) **System Settings route added**
   - New child route under `/system`:
     - Path: `/system/settings`
     - Component: `VgSettings`
     - Permissions: `config.read` + `config.set`
     - Title: `systemHome.tab.settings`
   - See the exact route block in the diff section above.

2) **No change to App User route paths**
   - The `/projects/:projectId/app-users` path still maps to `FieldKeyList`, but
     `FieldKeyList` now loads `vg-list.vue` via `src/util/load-async.js`.

3) **Formatting-only diff**
   - The large diff block in `src/routes.js` is mostly indentation and comment
     reflow; logic is unchanged outside the System Settings route block.

---

## 3) Dev Environment + Proxy Changes

### Dockerized Vite Dev Container

- Adds `Dockerfile.dev` for running client dev server + nginx proxy.
  - `Dockerfile.dev`

### Nginx proxy defaults (dev)

- Default backend target now `https://central.local`.
- SSL verification disabled for local dev.
- `/version.txt` now returns `development\n` (used by client).
  - `main.nginx.conf`

### Vite dev server updates

- `host: true` and `allowedHosts: ['central.local']` for remote host access.
  - `vite.config.js`

### Dev docs

- Dev server instructions.
- Walkthrough and technical documentation for VG App User Auth.
  - `docs/dev-server.md`
  - `docs/walkthrough.md`
  - `docs/vg-component-short-token-app-users.md`
  - `docs/TASK.md`

---

## 4) E2E Test Updates

- Default domain changed to `central.local` in CLI runner.
- Removes `--skip-install` option and always installs dependencies.
  - `e2e-tests/run-tests.sh`
- Uses `response.ok()` for Playwright response assertions.
  - `e2e-tests/backend-client.js`
  - `e2e-tests/global.setup.js`
- Teardown now always attempts project deletion.
  - `e2e-tests/global.teardown.js`

---

## Modified Upstream Files (Exact Changes)

- `CONTRIBUTING.md`
  - E2E default base URL updated from `http://central-dev.localhost:8989` to
    `http://central.local:8989`.
- `e2e-tests/backend-client.js`
  - Replaced `expect(response).toBeOK()` with `expect(response.ok()).toBeTruthy()`.
- `e2e-tests/global.setup.js`
  - Removed explicit 401 credential check; now uses `response.ok()` for success.
- `e2e-tests/global.teardown.js`
  - Removed early return on missing `PROJECT_ID`; always attempts deletion.
- `e2e-tests/run-tests.sh`
  - Default domain set to `central.local`.
  - Removed `--skip-install` option and always runs `npm ci` and
    `npx playwright install --with-deps`.
  - Removed `sudo -k` calls.
- `main.nginx.conf`
  - API proxy now targets `https://central.local` instead of `http://localhost:8383`.
  - Added `proxy_ssl_verify off` and `proxy_set_header Host central.local`.
  - `/version.txt` now returns `development\n` with `text/plain`.
- `src/components/system/home.vue`
  - Added a **Settings** tab under System.
- `src/components/toast.vue`
  - Adds `toast.options?.type` as a CSS class and styles success to green.
- `src/container/alerts.js`
  - `success()` and `info()` now pass explicit toast types; `info()` keeps
    `autoHide: false`.
- `src/locales/en.json5`
  - Added `systemHome.tab.settings` label.
  - Added `vgSettings` labels and validation message.
- `src/request-data/project.js`
  - Form Access uses `fieldKey.active === true` instead of `token` presence to
    include app users.
- `src/request-data/resources.js`
  - Added `systemSettings` requestData resource.
- `src/routes.js`
  - Added `/system/settings` route and ties it to `VgSettings`.
- `src/util/load-async.js`
  - `FieldKeyList` now loads `vg-list.vue`.
  - Added `VgSettings` loader.
- `src/util/request.js`
  - Added API paths for app-user auth (`login`, `update`, `reset`, `revoke`, `active`).
- `vite.config.js`
  - Set `host: true` and `allowedHosts: ['central.local']` for dev server.

---

## Diffs (Upstream -> vg-work)

```diff
diff --git a/CONTRIBUTING.md b/CONTRIBUTING.md
@@
-By default, tests run against `http://central-dev.localhost:8989`, but you can override it with `--protocol`, `--domain`, and `--port` CLI options.
+By default, tests run against `http://central.local:8989`, but you can override it with `--protocol`, `--domain`, and `--port` CLI options.
```

```diff
diff --git a/e2e-tests/backend-client.js b/e2e-tests/backend-client.js
@@
-    expect(response).toBeOK();
+    expect(response.ok()).toBeTruthy();
```

```diff
diff --git a/e2e-tests/global.setup.js b/e2e-tests/global.setup.js
@@
-  if (createProjectResponse.status() === 401) {
-    throw Error(`
-      Credentials check failed.
-
-      Confirm that:
-
-        1. the user '${user}' exists, and
-        2. their password matches the ODK_PASSWORD env var
-    `);
-  }
-
-  expect(createProjectResponse).toBeOK();
+  expect(createProjectResponse.ok()).toBeTruthy();
```

```diff
diff --git a/e2e-tests/global.teardown.js b/e2e-tests/global.teardown.js
@@
-  if (!projectId) return;
-
   const result = await fetch(`${appUrl}/v1/projects/${projectId}`, {
```

```diff
diff --git a/e2e-tests/run-tests.sh b/e2e-tests/run-tests.sh
@@
-ODK_DOMAIN="central-dev.localhost"
+ODK_DOMAIN="central.local"
@@
-SKIP_INSTALL=false
@@
-  --skip-install      Assume playwright is already available
@@
-    --skip-install) SKIP_INSTALL=true; shift ;;
@@
-  sudo -k
@@
-if [[ "$SKIP_INSTALL" = "true" ]]; then
-  log "Skipping npm install."
-else
-  log "Installing npm packages..."
-  npm ci
-fi
+log "Installing npm packages..."
+npm ci
@@
-if [[ "$SKIP_INSTALL" = "true" ]]; then
-  log "Skipping playwright install."
-else
-  log "Installing playwright deps..."
-  npx playwright install --with-deps
-  sudo -k
-fi
+log "Installing playwright deps..."
+npx playwright install --with-deps
```

```diff
diff --git a/main.nginx.conf b/main.nginx.conf
@@
-      proxy_pass http://localhost:8383;
+      proxy_pass https://central.local;
       proxy_redirect off;
+
+      # SSL configuration for local dev
+      proxy_ssl_verify off;
+      proxy_set_header Host central.local;
@@
-      return 404;
+      default_type text/plain;
+      return 200 "development\n";
```

```diff
diff --git a/src/components/system/home.vue b/src/components/system/home.vue
@@
         <li :class="tabClass('analytics')" role="presentation">
           <router-link :to="tabPath('analytics')">
             {{ $t('systemHome.tab.analytics') }}
           </router-link>
         </li>
+        <li :class="tabClass('settings')" role="presentation">
+          <router-link :to="tabPath('settings')">
+            {{ $t('systemHome.tab.settings') }}
+          </router-link>
+        </li>
```

```diff
diff --git a/src/components/toast.vue b/src/components/toast.vue
@@
-  <alert class="toast" :alert="toast"/>
+  <alert class="toast" :class="toast.options?.type" :alert="toast"/>
@@
+  &.success {
+    background-color: $color-success;
+  }
```

```diff
diff --git a/src/container/alerts.js b/src/container/alerts.js
@@
-    success: (message) => toast.show(message),
-    info: (message) => toast.show(message, { autoHide: false }),
+    success: (message) => toast.show(message, { type: 'success' }),
+    info: (message) => toast.show(message, { type: 'info', autoHide: false }),
```

```diff
diff --git a/src/locales/en.json5 b/src/locales/en.json5
@@
-      "analytics": "Usage Reporting"
+      "analytics": "Usage Reporting",
+      "settings": "App User Settings"
@@
   "router": {
     "unsavedChanges": "Are you sure you want to leave this page? Your changes might not be saved."
+  },
+  "vgSettings": {
+    "heading": "Configure App User Session Settings",
+    "ttl": "Session TTL (Days)",
+    "cap": "Max Sessions per User",
+    "alert": {
+      "invalidValues": "Values must be at least 1."
+    }
   }
```

```diff
diff --git a/src/request-data/project.js b/src/request-data/project.js
@@
-  const fieldKeys = createResource('fieldKeys', () => ({
-    withToken: computeIfExists(() =>
-      fieldKeys.filter(fieldKey => fieldKey.token != null))
-  }));
+  const fieldKeys = createResource('fieldKeys', () => ({
+    // Show all active app users in Form Access. Tokens are short-lived and not
+    // returned in listings, so rely on active flag rather than token presence.
+    withToken: computeIfExists(() =>
+      fieldKeys.filter(fieldKey => fieldKey.active === true))
+  }));
```

```diff
diff --git a/src/request-data/resources.js b/src/request-data/resources.js
@@
   createResource('analyticsConfig', noargs(setupOption));
+  createResource('systemSettings', noargs(setupOption));
```

```diff
diff --git a/src/routes.js b/src/routes.js
@@
         asyncRoute({
           path: 'analytics',
           component: 'AnalyticsList',
           loading: 'tab',
@@
           beforeEnter: () => (config.showsAnalytics ? true : '/404')
         }),
+        asyncRoute({
+          path: 'settings',
+          component: 'VgSettings',
+          loading: 'tab',
+          meta: {
+            validateData: {
+              currentUser: () => currentUser.can([
+                'config.read',
+                'config.set'
+              ])
+            },
+            title: () => [
+              i18n.t('systemHome.tab.settings'),
+              i18n.t('systemHome.title')
+            ],
+            fullWidth: true
+          }
+        })
```

```diff
diff --git a/src/util/load-async.js b/src/util/load-async.js
@@
-  .set('FieldKeyList', loader(() => import(
-    /* webpackChunkName: "component-field-key-list" */
-    '../components/field-key/list.vue'
-  )))
+  .set('FieldKeyList', loader(() => import(
+    /* webpackChunkName: "component-field-key-list" */
+    '../components/field-key/vg-list.vue'
+  )))
@@
+  .set('VgSettings', loader(() => import(
+    /* webpackChunkName: "component-vg-settings" */
+    '../components/system/vg-settings.vue'
+  )))
```

```diff
diff --git a/src/util/request.js b/src/util/request.js
@@
   fieldKeys: projectPath('/app-users'),
+  fieldKeyLogin: (projectId) => `/v1/projects/${projectId}/app-users/login`,
+  fieldKeyUpdate: (projectId, id) => `/v1/projects/${projectId}/app-users/${id}`,
+  fieldKeyResetPassword: (projectId, id) => `/v1/projects/${projectId}/app-users/${id}/password/reset`,
+  fieldKeyRevoke: (projectId, id) => `/v1/projects/${projectId}/app-users/${id}/revoke-admin`,
+  fieldKeyActive: (projectId, id) => `/v1/projects/${projectId}/app-users/${id}/active`,
```

```diff
diff --git a/vite.config.js b/vite.config.js
@@
+  host: true,
   port: 8989,
+  allowedHosts: ['central.local'],
```

---

## Files Added in vg-work

- `Dockerfile.dev`
- `docs/TASK.md`
- `docs/dev-server.md`
- `docs/vg-component-short-token-app-users.md`
- `docs/walkthrough.md`
- `src/components/field-key/vg-edit.vue`
- `src/components/field-key/vg-list.vue`
- `src/components/field-key/vg-new.vue`
- `src/components/field-key/vg-qr-panel.vue`
- `src/components/field-key/vg-reset-password.vue`
- `src/components/field-key/vg-restore.vue`
- `src/components/field-key/vg-revoke.vue`
- `src/components/field-key/vg-row.vue`
- `src/components/system/vg-settings.vue`
- `src/util/password-generator.js`
