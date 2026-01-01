# VG Core Client Edits (Required Log)

This log must include only VG fork modifications and exclude upstream master changes introduced by rebases or merges.

This file must document every edit made to upstream core client files
in `getodk/central-frontend`. Use it to keep rebases manageable.

## Log Format (one entry per change)

- Date:
- File:
- Change summary:
- Reason:
- Risk/notes:
- Related commits/PRs:

## Entries

- Date: 2026-01-01
  File: src/components/account/login.vue
  Change summary: Display login attempts remaining and lockout retry info from headers.
  Reason: Provide user feedback for web login hardening.
  Risk/notes: Low; UI messaging.
  Related commits/PRs: vg-work history

- Date: 2025-12-21
  File: CONTRIBUTING.md
  Change summary: Default e2e base URL updated to http://central.local:8989.
  Reason: Align docs with local dev domain.
  Risk/notes: Low risk; doc-only change.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/CONTRIBUTING.md b/CONTRIBUTING.md
  index e3d4b0c0..b448568c 100644
  --- a/CONTRIBUTING.md
  +++ b/CONTRIBUTING.md
  @@ -339,6 +339,6 @@ To learn more about stores and views, see [`/test/data/data-store.js`](/test/dat
   #### E2E Tests
   
   E2E tests can be run using `npm run test:e2e`. These tests assume the full Central stack is running — including central-backend, enketo, pyxform, and postgresql.
  -By default, tests run against `http://central-dev.localhost:8989`, but you can override it with `--protocol`, `--domain`, and `--port` CLI options.
  +By default, tests run against `http://central.local:8989`, but you can override it with `--protocol`, `--domain`, and `--port` CLI options.
   You can also set a custom `--user` and `--password` from the CLI.
   Finally, add the `--ui` flag to run tests in UI mode, which is useful for debugging.
  ```

- Date: 2025-12-21
  File: e2e-tests/run-tests.sh
  Change summary: Default domain central.local; remove --skip-install; always install deps.
  Reason: Standardize local e2e defaults and reduce inconsistent runs.
  Risk/notes: Medium; removes optional skip path and adds install cost.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/e2e-tests/run-tests.sh b/e2e-tests/run-tests.sh
  index 39c3fa9c..99f3666f 100755
  --- a/e2e-tests/run-tests.sh
  +++ b/e2e-tests/run-tests.sh
  @@ -5,12 +5,11 @@ log() {
   }
   
   # default values
  -ODK_DOMAIN="central-dev.localhost"
  +ODK_DOMAIN="central.local"
   ODK_PORT="8989"
   ODK_PROTOCOL="http://"
   ODK_USER="alice@example.com"
   ODK_PASSWORD="Testpassword@12345"
  -SKIP_INSTALL=false
   
   show_help() {
     cat <<EOF
  @@ -24,7 +23,6 @@ Options:
     --password=PASSWORD Set the protocol (default: $ODK_PASSWORD)
     --ui                Pass --ui option to playwright
     --help              Show this help message and exit
  -  --skip-install      Assume playwright is already available
   EOF
   }
   
  @@ -37,7 +35,6 @@ while [[ $# -gt 0 ]]; do
       --user=*) ODK_USER="${1#*=}"; shift ;;
       --password=*) ODK_PASSWORD="${1#*=}"; shift ;;
       --ui) PLAYWRIGHT_UI=true; shift ;;
  -    --skip-install) SKIP_INSTALL=true; shift ;;
       --help) show_help; exit 0 ;;
       *) echo "Unknown option: $1"; show_help; exit 1 ;;
     esac
  @@ -58,7 +55,6 @@ export PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS=1
   if [[ ${CI-} = true ]]; then
     log "Installing apt dependencies..."
     sudo apt-get install -y wait-for-it
  -  sudo -k
   
     log "Waiting for ODK Central to start..."
     wait-for-it $ODK_DOMAIN:$ODK_PORT --strict --timeout=60 -- echo '[e2e-tester] odk-central is UP!'
  @@ -70,23 +66,14 @@ if [[ ${CI-} = true ]]; then
     cd client
   fi
   
  -if [[ "$SKIP_INSTALL" = "true" ]]; then
  -  log "Skipping npm install."
  -else
  -  log "Installing npm packages..."
  -  npm ci
  -fi
  +log "Installing npm packages..."
  +npm ci
   
   cd e2e-tests
   log "Playwright: $(npx playwright --version)"
   
  -if [[ "$SKIP_INSTALL" = "true" ]]; then
  -  log "Skipping playwright install."
  -else
  -  log "Installing playwright deps..."
  -  npx playwright install --with-deps
  -  sudo -k
  -fi
  +log "Installing playwright deps..."
  +npx playwright install --with-deps
   
   log "Running playwright tests..."
   npx playwright test ${PLAYWRIGHT_UI:+--ui}
  ```

- Date: 2025-12-21
  File: main.nginx.conf
  Change summary: Proxy to https://central.local and return development version.txt.
  Reason: Dev proxy alignment with local TLS host.
  Risk/notes: Medium; dev-only nginx behavior change.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/main.nginx.conf b/main.nginx.conf
  index 69ce7e9a..b8d68469 100644
  --- a/main.nginx.conf
  +++ b/main.nginx.conf
  @@ -118,8 +118,13 @@ http {
   
   
       location ~ ^/v\d {
  -      proxy_pass http://localhost:8383;
  +      # Point to the Dockerized backend
  +      proxy_pass https://central.local;
         proxy_redirect off;
  +      
  +      # SSL configuration for local dev
  +      proxy_ssl_verify off;
  +      proxy_set_header Host central.local;
   
         # buffer requests, but not responses, so streaming out works.
         proxy_request_buffering on;
  @@ -149,7 +154,8 @@ http {
         return 200 "{}";
       }
       location /version.txt {
  -      return 404;
  +      default_type text/plain;
  +      return 200 "development\n";
       }
   
       # Only relevant for `npm run dev:build`, not `npm run dev`.
  ```

- Date: 2025-12-21
  File: src/components/system/home.vue
  Change summary: Added System Settings tab link.
  Reason: Expose new App User Settings UI.
  Risk/notes: Low.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/components/system/home.vue b/src/components/system/home.vue
  index c667d649..97e3abc7 100644
  --- a/src/components/system/home.vue
  +++ b/src/components/system/home.vue
  @@ -25,6 +25,11 @@ except according to the terms contained in the LICENSE file.
               {{ $t('systemHome.tab.analytics') }}
             </router-link>
           </li>
  +        <li :class="tabClass('settings')" role="presentation">
  +          <router-link :to="tabPath('settings')">
  +            {{ $t('systemHome.tab.settings') }}
  +          </router-link>
  +        </li>
         </template>
       </page-head>
       <page-body>
  ```

- Date: 2025-12-21
  File: src/components/toast.vue
  Change summary: Add toast type class and green success styling.
  Reason: Visual consistency for success alerts.
  Risk/notes: Low; minor CSS change.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/components/toast.vue b/src/components/toast.vue
  index fb56dfa9..fd3d3de6 100644
  --- a/src/components/toast.vue
  +++ b/src/components/toast.vue
  @@ -10,7 +10,7 @@ including this file, may be copied, modified, propagated, or distributed
   except according to the terms contained in the LICENSE file.
   -->
   <template>
  -  <alert class="toast" :alert="toast"/>
  +  <alert class="toast" :class="toast.options?.type" :alert="toast"/>
   </template>
   
   <script setup>
  @@ -28,6 +28,10 @@ const toast = inject('toast');
     background-color: #333;
     color: #fff;
   
  +  &.success {
  +    background-color: $color-success;
  +  }
  +
     .alert-cta {
       color: $color-action-light;
       &:hover, &:focus { color: $color-action-background; }
  ```

- Date: 2025-12-22
  File: src/util/load-async.js
  Change summary: Register VgProjectTelemetry async component.
  Reason: Add project telemetry UI under VG namespace.
  Risk/notes: Low; loader map update only.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/util/load-async.js b/src/util/load-async.js
  index 92da2ad3..05d8f1c7 100644
  --- a/src/util/load-async.js
  +++ b/src/util/load-async.js
  @@ -155,6 +155,10 @@ const loaders = new Map()
     .set('ProjectFormAccess', loader(() => import(
       /* webpackChunkName: "component-project-form-access" */
       '../components/project/form-access.vue'
     )))
  +  .set('VgProjectTelemetry', loader(() => import(
  +    /* webpackChunkName: "component-project-telemetry" */
  +    '../components/project/vg-telemetry.vue'
  +  )))
     .set('ProjectOverview', loader(() => import(
       /* webpackChunkName: "component-project-overview" */
       '../components/project/overview.vue'
     )))
  ```

- Date: 2025-12-22
  File: src/routes.js
  Change summary: Add /projects/:id/telemetry route gated by config.read.
  Reason: Surface project telemetry with filters/pagination.
  Risk/notes: Medium; new route entry and permissions gating.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/routes.js b/src/routes.js
  index 33f0f1ee..8ea819c8 100644
  --- a/src/routes.js
  +++ b/src/routes.js
  @@ -320,6 +320,19 @@
             },
             title: () => [i18n.t('resource.appUsers'), project.name]
           }
         }),
  +      asyncRoute({
  +        path: 'telemetry',
  +        component: 'VgProjectTelemetry',
  +        props: true,
  +        loading: 'tab',
  +        meta: {
  +          validateData: {
  +            currentUser: () => currentUser.can('config.read')
  +          },
  +          title: () => [i18n.t('projectShow.tab.telemetry'), project.name],
  +          fullWidth: true
  +        }
  +      }),
         asyncRoute({
           path: 'form-access',
           component: 'ProjectFormAccess',
  ```

- Date: 2025-12-22
  File: src/components/project/show.vue
  Change summary: Add Telemetry tab in project navigation.
  Reason: Provide navigation to project telemetry view.
  Risk/notes: Low; tab visibility depends on route permissions.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/components/project/show.vue b/src/components/project/show.vue
  index 6a21c0a8..1f2f48d0 100644
  --- a/src/components/project/show.vue
  +++ b/src/components/project/show.vue
  @@ -55,6 +55,11 @@
           <router-link :to="tabPath('app-users')">
             {{ $t('resource.appUsers') }}
           </router-link>
         </li>
  +      <li v-if="canRoute(tabPath('telemetry'))" :class="tabClass('telemetry')"
  +        role="presentation">
  +        <router-link :to="tabPath('telemetry')">
  +          {{ $t('projectShow.tab.telemetry') }}
  +        </router-link>
  +      </li>
         <li v-if="canRoute(tabPath('form-access'))"
           :class="tabClass('form-access')" role="presentation">
           <router-link :to="tabPath('form-access')">
  ```

- Date: 2025-12-22
  File: src/locales/en.json5
  Change summary: Add telemetry tab label and common “not available/unknown” strings.
  Reason: Provide English i18n for new telemetry UI and missing value labels.
  Risk/notes: Low.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/locales/en.json5 b/src/locales/en.json5
  index 3f012c9a..e0f9db9d 100644
  --- a/src/locales/en.json5
  +++ b/src/locales/en.json5
  @@ -15,7 +15,8 @@
   "projectShow": {
     "tab": {
       "formAccess": "Form Access",
  +    "telemetry": "Telemetry"
     }
   },
  @@ -426,7 +427,9 @@
     "no": "No",
     // This is shown if a search returned no results.
     "noResults": "No results",
  +  // This is shown for a missing or unavailable value.
  +  "notAvailable": "Not available",
     "noUndo": "This action cannot be undone.",
  @@ -446,6 +449,8 @@
     "table": "Table",
     "total": "Total",
     "totalSubmissions": "Total Submissions",
  +  // This is shown when an expected value is unknown.
  +  "unknown": "Unknown",
  ```

- Date: 2025-12-22
  File: src/util/load-async.js
  Change summary: Register VgProjectLoginHistory async component.
  Reason: Add project login history UI under VG namespace.
  Risk/notes: Low; loader map update only.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/util/load-async.js b/src/util/load-async.js
  index 05d8f1c7..10c9fa21 100644
  --- a/src/util/load-async.js
  +++ b/src/util/load-async.js
  @@ -155,6 +155,10 @@ const loaders = new Map()
     .set('ProjectFormAccess', loader(() => import(
       /* webpackChunkName: "component-project-form-access" */
       '../components/project/form-access.vue'
     )))
  +  .set('VgProjectLoginHistory', loader(() => import(
  +    /* webpackChunkName: "component-project-login-history" */
  +    '../components/project/vg-login-history.vue'
  +  )))
     .set('VgProjectTelemetry', loader(() => import(
       /* webpackChunkName: "component-project-telemetry" */
       '../components/project/vg-telemetry.vue'
     )))
  ```

- Date: 2025-12-22
  File: src/routes.js
  Change summary: Add /projects/:id/login-history route and preserve data between tabs.
  Reason: Provide project login history tab with filters/pagination.
  Risk/notes: Medium; new route entry and project-tab preservation.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/routes.js b/src/routes.js
  index 8ea819c8..21c1e2af 100644
  --- a/src/routes.js
  +++ b/src/routes.js
  @@ -333,6 +333,19 @@
             title: () => [i18n.t('projectShow.tab.telemetry'), project.name],
             fullWidth: true
           }
         }),
  +      asyncRoute({
  +        path: 'login-history',
  +        component: 'VgProjectLoginHistory',
  +        props: true,
  +        loading: 'tab',
  +        meta: {
  +          validateData: {
  +            project: () => project.permits('field_key.list')
  +          },
  +          title: () => [i18n.t('projectShow.tab.loginHistory'), project.name],
  +          fullWidth: true
  +        }
  +      }),
         asyncRoute({
           path: 'form-access',
           component: 'ProjectFormAccess',
  @@ -853,6 +853,7 @@
    const projectRoutes = [
      'ProjectOverview',
      'ProjectUserList',
      'FieldKeyList',
      'VgProjectTelemetry',
  +    'VgProjectLoginHistory',
      'ProjectFormAccess',
      'DatasetList',
      'ProjectSettings'
    ];
  ```

- Date: 2025-12-22
  File: src/components/project/show.vue
  Change summary: Add Login History tab in project navigation.
  Reason: Provide navigation to project login history view.
  Risk/notes: Low; tab visibility depends on route permissions.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/components/project/show.vue b/src/components/project/show.vue
  index 1f2f48d0..55be9b90 100644
  --- a/src/components/project/show.vue
  +++ b/src/components/project/show.vue
  @@ -60,6 +60,11 @@
           <router-link :to="tabPath('telemetry')">
             {{ $t('projectShow.tab.telemetry') }}
           </router-link>
         </li>
  +      <li v-if="canRoute(tabPath('login-history'))" :class="tabClass('login-history')"
  +        role="presentation">
  +        <router-link :to="tabPath('login-history')">
  +          {{ $t('projectShow.tab.loginHistory') }}
  +        </router-link>
  +      </li>
         <li v-if="canRoute(tabPath('form-access'))"
           :class="tabClass('form-access')" role="presentation">
           <router-link :to="tabPath('form-access')">
  ```

- Date: 2025-12-22
  File: src/locales/en.json5
  Change summary: Add login history tab label.
  Reason: Provide English i18n for project login history tab.
  Risk/notes: Low.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/locales/en.json5 b/src/locales/en.json5
  index e0f9db9d..3d3c0d1a 100644
  --- a/src/locales/en.json5
  +++ b/src/locales/en.json5
  @@ -15,7 +15,8 @@
   "projectShow": {
     "tab": {
       "formAccess": "Form Access",
       "telemetry": "Telemetry",
  +    "loginHistory": "Login History"
     }
   },
  ```

- Date: 2025-12-22
  File: src/util/request.js
  Change summary: Add app-user session revoke API path helper.
  Reason: Support per-session deactivation in login history UI.
  Risk/notes: Low; helper only.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/src/util/request.js b/src/util/request.js
  index 96d1e5cc..76b2d4e0 100644
  --- a/src/util/request.js
  +++ b/src/util/request.js
  @@ -195,6 +195,8 @@ export const apiPaths = {
     projectAppUserSessions: (projectId, query = undefined) =>
       `/v1/projects/${projectId}/app-users/sessions${queryString(query)}`,
  +  projectAppUserSessionRevoke: (projectId, sessionId) =>
  +    `/v1/projects/${projectId}/app-users/sessions/${sessionId}/revoke`,
     systemAppUserTelemetry: (query = undefined) =>
       `/v1/system/app-users/telemetry${queryString(query)}`,
  ```

- Date: 2025-12-21
  File: src/container/alerts.js
  Change summary: Pass explicit toast types for success/info.
  Reason: Enable toast styling by type.
  Risk/notes: Low.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/container/alerts.js b/src/container/alerts.js
  index c2b9d6cd..ec87595d 100644
  --- a/src/container/alerts.js
  +++ b/src/container/alerts.js
  @@ -62,8 +62,8 @@ export default () => {
           : (toast.options.autoHide ? 'success' : 'info');
       },
   
  -    success: (message) => toast.show(message),
  -    info: (message) => toast.show(message, { autoHide: false }),
  +    success: (message) => toast.show(message, { type: 'success' }),
  +    info: (message) => toast.show(message, { type: 'info', autoHide: false }),
       danger: (message) => redAlert.show(message)
   
       // There is intentionally no hide() method. It's not clear what the behavior
  ```

- Date: 2025-12-21
  File: src/locales/en.json5
  Change summary: Added System Settings tab label and vgSettings strings.
  Reason: New App User Settings UI copy.
  Risk/notes: Low.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/locales/en.json5 b/src/locales/en.json5
  index b4a17772..697d8819 100644
  --- a/src/locales/en.json5
  +++ b/src/locales/en.json5
  @@ -30,7 +30,8 @@
       "title": "System Management",
       "tab": {
         "audits": "Server Audit Logs",
  -      "analytics": "Usage Reporting"
  +      "analytics": "Usage Reporting",
  +      "settings": "App User Settings"
       }
     },
     // This is the name of a user Role.
  @@ -528,5 +529,13 @@
     },
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
   }
  ```

- Date: 2025-12-21
  File: src/request-data/project.js
  Change summary: Form Access uses active flag, not token presence.
  Reason: Tokens are short-lived and not returned in listings.
  Risk/notes: Medium; affects app-user visibility in Form Access.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/request-data/project.js b/src/request-data/project.js
  index 18d4c106..bc327bb6 100644
  --- a/src/request-data/project.js
  +++ b/src/request-data/project.js
  @@ -25,8 +25,10 @@ export default () => {
     }));
     const formSummaryAssignments = createResource('formSummaryAssignments');
     const fieldKeys = createResource('fieldKeys', () => ({
  +    // Show all active app users in Form Access. Tokens are short-lived and not
  +    // returned in listings, so rely on active flag rather than token presence.
       withToken: computeIfExists(() =>
  -      fieldKeys.filter(fieldKey => fieldKey.token != null))
  +      fieldKeys.filter(fieldKey => fieldKey.active === true))
     }));
   
     watchSyncEffect(() => {
  ```

- Date: 2025-12-21
  File: src/request-data/resources.js
  Change summary: Added systemSettings resource.
  Reason: Supports System Settings UI data fetch.
  Risk/notes: Low.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/request-data/resources.js b/src/request-data/resources.js
  index cb65ff70..7833a710 100644
  --- a/src/request-data/resources.js
  +++ b/src/request-data/resources.js
  @@ -51,6 +51,7 @@ export default (container, createResource) => {
         })
     }));
     createResource('analyticsConfig', noargs(setupOption));
  +  createResource('systemSettings', noargs(setupOption));
     createResource('roles', (roles) => ({
       bySystem: computeIfExists(() => {
         // Using Object.create(null) in case there is a role whose `system`
  ```

- Date: 2025-12-21
  File: src/routes.js
  Change summary: Added /system/settings route; remainder mostly formatting.
  Reason: Wire new App User Settings UI.
  Risk/notes: Low; routing change for admins.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/routes.js b/src/routes.js
  index 51015830..f7e82b97 100644
  --- a/src/routes.js
  +++ b/src/routes.js
  @@ -16,785 +16,803 @@ import AsyncRoute from './components/async-route.vue';
   import { routeProps } from './util/router';
   
   export default (container) => {
  -/* eslint-disable indent */ // TODO/vue3
  -/*
  -Lazy-Loading Routes
  --------------------
  -
  -We lazy-load all routes except for /login. We show a loading message while the
  -async component is loading and an alert if there is a load error. Note that
  -while Vue provides similar loading-state functionality for async components, Vue
  -Router does not support it directly: see
  -https://github.com/vuejs/vue-router/pull/2140. Instead, we use a wrapper
  -component, AsyncRoute, that will load and render the async component.
  -
  -Every navigation is asynchronous, but because we use a wrapper component, the
  -navigation should be completed almost instantly, as a microtask. For example, if
  -a user clicks a link to /users but has not loaded the UserList component yet,
  -they will navigate to /users almost instantly, where they will see a loading
  -message; they will not stay at the previous route while UserList loads. This
  -approach should make it easier to reason about navigation. However, one downside
  -is that an async component cannot use an in-component navigation guard.
  -
  -Route Names
  ------------
  -
  -All bottom-level routes should have a name. When lazy-loading routes, a
  -bottom-level route is automatically given the same name as its component by
  -default. Only bottom-level routes should have a name: otherwise, Vue Router will
  -log a warning (see https://github.com/vuejs/vue-router/issues/629).
  -
  -In general, we try not to use route names to drive behavior. We use routes names
  -with the preserveData meta field below, but outside this file, we prefer route
  -paths to route names where possible.
  -
  -Route Meta Fields
  ------------------
  -
  -The following meta fields are supported for bottom-level routes:
  -
  -  Login/Logout
  -  ------------
  -
  -  - restoreSession (default: true). The router looks to restoreSession right
  -    after the user has navigated to Frontend, when the router is navigating to
  -    the first route. If restoreSession is `true` for the first route, the router
  -    will attempt to restore the user's session before navigating to the route.
  -    Note that even if restoreSession is `false`, the router will not delete any
  -    cookie that is set. That means that if the user navigates to a route for
  -    which `restoreSession` is `false`, then opens a new tab and navigates to a
  -    route for which `restoreSession` is `true`, the user's session may be
  -    restored in the second tab.
  -  - requireLogin (default: true). Indicates whether the user must be logged in
  -    in order to navigate to the route. If an anonymous user (a user who is
  -    logged out) navigates to the route, they will be redirected to login.
  -  - requireAnonymity (default: false)
  -
  -    Indicates whether the user must be anonymous (logged out) in order to
  -    navigate to the route. If a user is logged in and navigates to the route,
  -    they will be redirected to the root page.
  -
  -    In almost all cases, a route either requires login or requires anonymity.
  -    However, NotFound requires neither: a user can navigate to NotFound whether
  -    they are logged in or anonymous.
  -
  -  - skipAutoLogout (default: false): If `true`, no alert will be displayed when
  -    session is about to expire. Also user will be not be redirected to login
  -    page when session has expired.
  -
  -  requestData
  +  /* eslint-disable indent */ // TODO/vue3
  +  /*
  +  Lazy-Loading Routes
  +  -------------------
  +  
  +  We lazy-load all routes except for /login. We show a loading message while the
  +  async component is loading and an alert if there is a load error. Note that
  +  while Vue provides similar loading-state functionality for async components, Vue
  +  Router does not support it directly: see
  +  https://github.com/vuejs/vue-router/pull/2140. Instead, we use a wrapper
  +  component, AsyncRoute, that will load and render the async component.
  +  
  +  Every navigation is asynchronous, but because we use a wrapper component, the
  +  navigation should be completed almost instantly, as a microtask. For example, if
  +  a user clicks a link to /users but has not loaded the UserList component yet,
  +  they will navigate to /users almost instantly, where they will see a loading
  +  message; they will not stay at the previous route while UserList loads. This
  +  approach should make it easier to reason about navigation. However, one downside
  +  is that an async component cannot use an in-component navigation guard.
  +  
  +  Route Names
     -----------
  +  
  +  All bottom-level routes should have a name. When lazy-loading routes, a
  +  bottom-level route is automatically given the same name as its component by
  +  default. Only bottom-level routes should have a name: otherwise, Vue Router will
  +  log a warning (see https://github.com/vuejs/vue-router/issues/629).
  +  
  +  In general, we try not to use route names to drive behavior. We use routes names
  +  with the preserveData meta field below, but outside this file, we prefer route
  +  paths to route names where possible.
  +  
  +  Route Meta Fields
  +  -----------------
  +  
  +  The following meta fields are supported for bottom-level routes:
  +  
  +    Login/Logout
  +    ------------
  +  
  +    - restoreSession (default: true). The router looks to restoreSession right
  +      after the user has navigated to Frontend, when the router is navigating to
  +      the first route. If restoreSession is `true` for the first route, the router
  +      will attempt to restore the user's session before navigating to the route.
  +      Note that even if restoreSession is `false`, the router will not delete any
  +      cookie that is set. That means that if the user navigates to a route for
  +      which `restoreSession` is `false`, then opens a new tab and navigates to a
  +      route for which `restoreSession` is `true`, the user's session may be
  +      restored in the second tab.
  +    - requireLogin (default: true). Indicates whether the user must be logged in
  +      in order to navigate to the route. If an anonymous user (a user who is
  +      logged out) navigates to the route, they will be redirected to login.
  +    - requireAnonymity (default: false)
  +  
  +      Indicates whether the user must be anonymous (logged out) in order to
  +      navigate to the route. If a user is logged in and navigates to the route,
  +      they will be redirected to the root page.
  +  
  +      In almost all cases, a route either requires login or requires anonymity.
  +      However, NotFound requires neither: a user can navigate to NotFound whether
  +      they are logged in or anonymous.
  +  
  +    - skipAutoLogout (default: false): If `true`, no alert will be displayed when
  +      session is about to expire. Also user will be not be redirected to login
  +      page when session has expired.
  +  
  +    requestData
  +    -----------
  +  
  +    - preserveData (optional). By default, whenever the route changes, all
  +      app-wide requestData resources are cleared. preserveData specifies
  +      exceptions to that rule. preserveData holds an array of functions, each of
  +      which can preserve one or more app-wide resources. Each function is passed
  +      the new and old routes and should return either an array of resources to
  +      preserve or a boolean. If a function returns `true`, all app-wide resources
  +      will be preserved. preserveData meta fields are set in a section below.
  +      preserveData does not affect local resources, which are tied to the
  +      lifecycle of the component, not the route.
  +    - validateData (optional)
  +  
  +      Some routes can be navigated to only if certain conditions are met. For
  +      example, the user may have to be able to perform certain verbs sitewide.
  +  
  +      validateData checks that conditions about requestData are met. (Perhaps more
  +      precisely, it checks that no condition is violated.) Here is an example
  +      value:
  +  
  +      {
  +        // Specifies a condition for currentUser: the user must be able to
  +        // user.list sitewide.
  +        currentUser: () => currentUser.can('user.list'),
  +        // Specifies a condition for `project`: the user must be able to
  +        // assignment.list for the project.
  +        project: () => project.permits('assignment.list')
  +      }
  +  
  +      Before the user navigates to the route, any data that will be preserved
  +      after the route change is checked for whether it meets the specified
  +      conditions. If any condition is violated, the user is redirected to /.
  +  
  +      There may be data that will be cleared after the route change or that has
  +      never been requested, but will be requested after the component is created.
  +      That data can't be checked in a navigation guard, so a watcher is also added
  +      for each condition; the watcher will check the associated data as soon as it
  +      exists. The watcher will also continue watching the data, checking that it
  +      continues to meet the condition.
  +  
  +    Responsive Document Titles
  +    --------------------------
  +  
  +    - title
  +  
  +      The router updates the document title (text that appears in the browser tab
  +      and history) after a route is changed. It looks at the current route and
  +      calls that route's `title` function, which returns an array of strings to
  +      combine to build the full document title.
  +  
  +      The `title` function likely uses the i18n translations (specified in
  +      `src/locales/en.json5`). It may also use fields of a particular resource
  +      (e.g. `project.name`).
  +  
  +      The IMPORTANT thing to note is that most resources are loaded asynchronously
  +      after the page is loaded, so the Project, Form, User, etc. resource may not
  +      have data right away. Because of that, the `title` function should account
  +      for the possibility of a resource that does not have data yet. (Note that
  +      the array that the `title` function returns may contain `null` elements.)
  +      The result of the `title` function will be watched, and the document title
  +      will be updated once the resource has data. If a resource already has data,
  +      from viewing different pages about the same project or form for example, the
  +      proper title will be set immediately after the navigation is confirmed.
  +  
  +      Here is an example `title` function with
  +      * i18n
  +      * fetching information from a resource that might not have data
  +  
  +      () => [
  +        i18n.t('title.project.appUsers'),
  +        project.name // project.name may be `null`
  +      ]
  +  
  +    Other
  +    -----
  +  
  +    - fullWidth (default: false). If fullWidth is `true`, and the route renders a
  +      PageBody component, then the PageBody will use the full width of the page.
  +      By default, PageBody has a max width.
  +  
  +    - standalone (default: false): If standalone is `true` then application layout
  +      elements like navigation bar, background color, etc are not rendered.
  +  
  +  */
  +
  +  /*
  +  asyncRoute() returns a config for a route that is lazy-loaded. Specify a
  +  standard route config to asyncRoute() with the following additions:
  +  
  +    - component. Instead of component options, specify the component name.
  +    - loading. Indicates how to render the loading message, which depends on how
  +      the component fits into the larger page structure. Specify 'page' if the
  +      component renders a page; specify 'tab' if it renders a tab pane.
  +    - key (optional)
  +  
  +      The `key` option determines whether a component is re-rendered after a route
  +      update, for example, after a param change.
  +  
  +      By default, we use a mechanism similar to the `key` attribute to re-render
  +      the component whenever the route path changes. In other words, we opt out of
  +      the default Vue Router behavior, which reuses the component instance.
  +      Re-rendering the component simplifies component code and makes it easier to
  +      reason about component state.
  +  
  +      However, when using nested routes, we may wish to reuse a parent component
  +      instance while re-rendering a child component. To reuse a component instance
  +      associated with a route, specify a function that returns a value for the
  +      `key` attribute. If the value does not change after the route update, the
  +      component instance will be reused. For example, to reuse a component
  +      instance associated with a parent route, you can specify a function that
  +      returns the part of the path that corresponds to the parent route. See the
  +      routes below for specific examples.
  +  */
  +  const asyncRoute = (options) => {
  +    const { component, props, loading, key, ...config } = options;
  +    config.component = AsyncRoute;
  +    // Props for AsyncRoute
  +    config.props = (route) => ({
  +      componentName: component,
  +      // Props for the async component
  +      props: routeProps(route, props),
  +      loading,
  +      k: key != null ? key(route.params) : route.path
  +    });
  +    if (config.name == null && config.children == null) config.name = component;
  +    if (config.meta == null) config.meta = {};
  +    config.meta.asyncRoute = { componentName: component };
  +    return config;
  +  };
   
  -  - preserveData (optional). By default, whenever the route changes, all
  -    app-wide requestData resources are cleared. preserveData specifies
  -    exceptions to that rule. preserveData holds an array of functions, each of
  -    which can preserve one or more app-wide resources. Each function is passed
  -    the new and old routes and should return either an array of resources to
  -    preserve or a boolean. If a function returns `true`, all app-wide resources
  -    will be preserved. preserveData meta fields are set in a section below.
  -    preserveData does not affect local resources, which are tied to the
  -    lifecycle of the component, not the route.
  -  - validateData (optional)
  -
  -    Some routes can be navigated to only if certain conditions are met. For
  -    example, the user may have to be able to perform certain verbs sitewide.
  -
  -    validateData checks that conditions about requestData are met. (Perhaps more
  -    precisely, it checks that no condition is violated.) Here is an example
  -    value:
  +  const { i18n, requestData, config } = container;
  +  const { currentUser, project, form, dataset } = requestData;
  +  const routes = [
  +    asyncRoute({
  +      path: '/load-error',
  +      component: 'ConfigError',
  +      loading: 'page',
  +      meta: {
  +        requireLogin: false,
  +        requireAnonymity: true,
  +        title: () => [i18n.t('common.error')]
  +      },
  +      beforeEnter: () => (config.loadError == null ? '/login' : true)
  +    }),
   
       {
  -      // Specifies a condition for currentUser: the user must be able to
  -      // user.list sitewide.
  -      currentUser: () => currentUser.can('user.list'),
  -      // Specifies a condition for `project`: the user must be able to
  -      // assignment.list for the project.
  -      project: () => project.permits('assignment.list')
  -    }
  -
  -    Before the user navigates to the route, any data that will be preserved
  -    after the route change is checked for whether it meets the specified
  -    conditions. If any condition is violated, the user is redirected to /.
  -
  -    There may be data that will be cleared after the route change or that has
  -    never been requested, but will be requested after the component is created.
  -    That data can't be checked in a navigation guard, so a watcher is also added
  -    for each condition; the watcher will check the associated data as soon as it
  -    exists. The watcher will also continue watching the data, checking that it
  -    continues to meet the condition.
  -
  -  Responsive Document Titles
  -  --------------------------
  -
  -  - title
  -
  -    The router updates the document title (text that appears in the browser tab
  -    and history) after a route is changed. It looks at the current route and
  -    calls that route's `title` function, which returns an array of strings to
  -    combine to build the full document title.
  -
  -    The `title` function likely uses the i18n translations (specified in
  -    `src/locales/en.json5`). It may also use fields of a particular resource
  -    (e.g. `project.name`).
  -
  -    The IMPORTANT thing to note is that most resources are loaded asynchronously
  -    after the page is loaded, so the Project, Form, User, etc. resource may not
  -    have data right away. Because of that, the `title` function should account
  -    for the possibility of a resource that does not have data yet. (Note that
  -    the array that the `title` function returns may contain `null` elements.)
  -    The result of the `title` function will be watched, and the document title
  -    will be updated once the resource has data. If a resource already has data,
  -    from viewing different pages about the same project or form for example, the
  -    proper title will be set immediately after the navigation is confirmed.
  -
  -    Here is an example `title` function with
  -    * i18n
  -    * fetching information from a resource that might not have data
  -
  -    () => [
  -      i18n.t('title.project.appUsers'),
  -      project.name // project.name may be `null`
  -    ]
  -
  -  Other
  -  -----
  -
  -  - fullWidth (default: false). If fullWidth is `true`, and the route renders a
  -    PageBody component, then the PageBody will use the full width of the page.
  -    By default, PageBody has a max width.
  -
  -  - standalone (default: false): If standalone is `true` then application layout
  -    elements like navigation bar, background color, etc are not rendered.
  -
  -*/
  -
  -/*
  -asyncRoute() returns a config for a route that is lazy-loaded. Specify a
  -standard route config to asyncRoute() with the following additions:
  -
  -  - component. Instead of component options, specify the component name.
  -  - loading. Indicates how to render the loading message, which depends on how
  -    the component fits into the larger page structure. Specify 'page' if the
  -    component renders a page; specify 'tab' if it renders a tab pane.
  -  - key (optional)
  -
  -    The `key` option determines whether a component is re-rendered after a route
  -    update, for example, after a param change.
  -
  -    By default, we use a mechanism similar to the `key` attribute to re-render
  -    the component whenever the route path changes. In other words, we opt out of
  -    the default Vue Router behavior, which reuses the component instance.
  -    Re-rendering the component simplifies component code and makes it easier to
  -    reason about component state.
  -
  -    However, when using nested routes, we may wish to reuse a parent component
  -    instance while re-rendering a child component. To reuse a component instance
  -    associated with a route, specify a function that returns a value for the
  -    `key` attribute. If the value does not change after the route update, the
  -    component instance will be reused. For example, to reuse a component
  -    instance associated with a parent route, you can specify a function that
  -    returns the part of the path that corresponds to the parent route. See the
  -    routes below for specific examples.
  -*/
  -const asyncRoute = (options) => {
  -  const { component, props, loading, key, ...config } = options;
  -  config.component = AsyncRoute;
  -  // Props for AsyncRoute
  -  config.props = (route) => ({
  -    componentName: component,
  -    // Props for the async component
  -    props: routeProps(route, props),
  -    loading,
  -    k: key != null ? key(route.params) : route.path
  -  });
  -  if (config.name == null && config.children == null) config.name = component;
  -  if (config.meta == null) config.meta = {};
  -  config.meta.asyncRoute = { componentName: component };
  -  return config;
  -};
  -
  -const { i18n, requestData, config } = container;
  -const { currentUser, project, form, dataset } = requestData;
  -const routes = [
  -  asyncRoute({
  -    path: '/load-error',
  -    component: 'ConfigError',
  -    loading: 'page',
  -    meta: {
  -      requireLogin: false,
  -      requireAnonymity: true,
  -      title: () => [i18n.t('common.error')]
  -    },
  -    beforeEnter: () => (config.loadError == null ? '/login' : true)
  -  }),
  -
  -  {
  -    path: '/login',
  -    name: 'AccountLogin',
  -    component: AccountLogin,
  -    meta: {
  -      requireLogin: false,
  -      requireAnonymity: true,
  -      title: () => [i18n.t('action.logIn')]
  -    }
  -  },
  -  asyncRoute({
  -    path: '/reset-password',
  -    component: 'AccountResetPassword',
  -    loading: 'page',
  -    meta: {
  -      requireLogin: false,
  -      requireAnonymity: true,
  -      title: () => [i18n.t('title.resetPassword')]
  -    },
  -    beforeEnter: () => (config.oidcEnabled ? '/404' : true)
  -  }),
  -  asyncRoute({
  -    path: '/account/claim',
  -    component: 'AccountClaim',
  -    loading: 'page',
  -    meta: {
  -      restoreSession: false,
  -      requireLogin: false,
  -      requireAnonymity: true,
  -      title: () => [i18n.t('title.setPassword')]
  +      path: '/login',
  +      name: 'AccountLogin',
  +      component: AccountLogin,
  +      meta: {
  +        requireLogin: false,
  +        requireAnonymity: true,
  +        title: () => [i18n.t('action.logIn')]
  +      }
       },
  -    beforeEnter: () => (config.oidcEnabled ? '/404' : true)
  -  }),
  +    asyncRoute({
  +      path: '/reset-password',
  +      component: 'AccountResetPassword',
  +      loading: 'page',
  +      meta: {
  +        requireLogin: false,
  +        requireAnonymity: true,
  +        title: () => [i18n.t('title.resetPassword')]
  +      },
  +      beforeEnter: () => (config.oidcEnabled ? '/404' : true)
  +    }),
  +    asyncRoute({
  +      path: '/account/claim',
  +      component: 'AccountClaim',
  +      loading: 'page',
  +      meta: {
  +        restoreSession: false,
  +        requireLogin: false,
  +        requireAnonymity: true,
  +        title: () => [i18n.t('title.setPassword')]
  +      },
  +      beforeEnter: () => (config.oidcEnabled ? '/404' : true)
  +    }),
   
  -  asyncRoute({
  -    path: '/',
  -    component: 'Home',
  -    loading: 'page',
  -    meta: {
  -      title: () => [i18n.t('resource.projects')]
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)',
  -    component: 'ProjectShow',
  -    props: true,
  -    loading: 'page',
  -    key: ({ projectId }) => `/projects/${projectId}`,
  -    children: [
  -      asyncRoute({
  -        path: '',
  -        component: 'ProjectOverview',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits('form.list') || project.permits('open_form.list')
  -          },
  -          title: () => [i18n.t('resource.forms'), project.name]
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'users',
  -        component: 'ProjectUserList',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits([
  -              'assignment.list',
  -              'assignment.create',
  -              'assignment.delete'
  -            ])
  -          },
  -          title: () => [i18n.t('resource.projectRoles'), project.name]
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'app-users',
  -        component: 'FieldKeyList',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits([
  -              'field_key.list',
  -              'field_key.create',
  -              'session.end'
  -            ])
  -          },
  -          title: () => [i18n.t('resource.appUsers'), project.name]
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'form-access',
  -        component: 'ProjectFormAccess',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits([
  -              'form.list',
  -              'field_key.list',
  -              'assignment.list',
  -              'project.update',
  -              'form.update',
  -              'assignment.create',
  -              'assignment.delete'
  -            ])
  -          },
  -          title: () => [i18n.t('projectShow.tab.formAccess'), project.name],
  -          fullWidth: true
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'entity-lists',
  -        component: 'DatasetList',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits(['dataset.list', 'entity.list'])
  -          },
  -          title: () => [i18n.t('resource.entities'), project.name]
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'settings',
  -        component: 'ProjectSettings',
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits(['project.update'])
  -          },
  -          title: () => [i18n.t('common.tab.settings'), project.name]
  -        }
  -      })
  -    ]
  -  }),
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId',
  -    component: 'FormShow',
  -    props: true,
  -    loading: 'page',
  -    key: ({ projectId, xmlFormId }) =>
  -      `/projects/${projectId}/forms/${encodeURIComponent(xmlFormId)}`,
  -    children: [
  -      asyncRoute({
  -        path: 'versions',
  -        component: 'FormVersionList',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            // Including submission.list in order to exclude Data Collectors.
  -            project: () => project.permits(['form.read', 'submission.list']),
  -            form: () => form.publishedAt != null
  -          },
  -          title: () => [i18n.t('formHead.tab.versions'), form.nameOrId]
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'submissions',
  -        alias: '',
  -        component: 'FormSubmissions',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits([
  -              'form.read',
  -              'submission.list',
  -              'submission.read'
  -            ]),
  -            form: () => form.publishedAt != null
  -          },
  -          title: () => [i18n.t('resource.submissions'), form.nameOrId],
  -          fullWidth: true
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'public-links',
  -        component: 'PublicLinkList',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits([
  -              'form.read',
  -              'public_link.list',
  -              'public_link.create',
  -              'session.end'
  -            ]),
  -            form: () => form.publishedAt != null
  -          },
  -          title: () => [i18n.t('formHead.tab.publicAccess'), form.nameOrId]
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'settings',
  -        component: 'FormSettings',
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits([
  -              'form.read',
  -              'form.update',
  -              'form.delete'
  -            ]),
  -            form: () => form.publishedAt != null
  -          },
  -          title: () => [i18n.t('common.tab.settings'), form.nameOrId]
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'draft',
  -        component: 'FormEdit',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            project: () => project.permits([
  -              'form.read',
  -              'form.update',
  -              'form.delete',
  -              'dataset.list',
  -              'entity.list',
  -              'submission.list',
  -              'submission.read'
  -            ])
  -          },
  -          title: () => [i18n.t('formHead.tab.editForm'), form.nameOrId],
  -          fullWidth: true
  -        }
  -      })
  -    ]
  -  }),
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/submissions/:instanceId',
  -    component: 'SubmissionShow',
  -    props: true,
  -    loading: 'page',
  -    meta: {
  -      validateData: {
  -        project: () => project.permits('submission.read')
  +    asyncRoute({
  +      path: '/',
  +      component: 'Home',
  +      loading: 'page',
  +      meta: {
  +        title: () => [i18n.t('resource.projects')]
         }
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/preview',
  -    component: 'FormPreview',
  -    props: (route) => ({
  -      ...route.params,
  -      draft: false
       }),
  -    loading: 'page',
  -    meta: {
  -      standalone: true,
  -      title: () => [`✨ ${i18n.t('resource.formPreview')}`, form.nameOrId ?? '']
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/draft/preview',
  -    name: 'FormDraftPreview',
  -    component: 'FormPreview',
  -    props: (route) => ({
  -      ...route.params,
  -      draft: true
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)',
  +      component: 'ProjectShow',
  +      props: true,
  +      loading: 'page',
  +      key: ({ projectId }) => `/projects/${projectId}`,
  +      children: [
  +        asyncRoute({
  +          path: '',
  +          component: 'ProjectOverview',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits('form.list') || project.permits('open_form.list')
  +            },
  +            title: () => [i18n.t('resource.forms'), project.name]
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'users',
  +          component: 'ProjectUserList',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits([
  +                'assignment.list',
  +                'assignment.create',
  +                'assignment.delete'
  +              ])
  +            },
  +            title: () => [i18n.t('resource.projectRoles'), project.name]
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'app-users',
  +          component: 'FieldKeyList',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits([
  +                'field_key.list',
  +                'field_key.create',
  +                'session.end'
  +              ])
  +            },
  +            title: () => [i18n.t('resource.appUsers'), project.name]
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'form-access',
  +          component: 'ProjectFormAccess',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits([
  +                'form.list',
  +                'field_key.list',
  +                'assignment.list',
  +                'project.update',
  +                'form.update',
  +                'assignment.create',
  +                'assignment.delete'
  +              ])
  +            },
  +            title: () => [i18n.t('projectShow.tab.formAccess'), project.name],
  +            fullWidth: true
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'entity-lists',
  +          component: 'DatasetList',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits(['dataset.list', 'entity.list'])
  +            },
  +            title: () => [i18n.t('resource.entities'), project.name]
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'settings',
  +          component: 'ProjectSettings',
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits(['project.update'])
  +            },
  +            title: () => [i18n.t('common.tab.settings'), project.name]
  +          }
  +        })
  +      ]
       }),
  -    loading: 'page',
  -    meta: {
  -      standalone: true,
  -      title: () => [`✨ ${i18n.t('resource.formPreview')}`, form.nameOrId ? `${form.nameOrId} (${i18n.t('resource.draft')})` : '']
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)/entity-lists/:datasetName',
  -    component: 'DatasetShow',
  -    props: true,
  -    loading: 'page',
  -    key: ({ projectId, datasetName }) =>
  -      `/projects/${projectId}/entity-lists/${encodeURIComponent(datasetName)}`,
  -    children: [
  -      asyncRoute({
  -        path: 'properties',
  -        component: 'DatasetOverview',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          title: () => [i18n.t('resource.properties'), dataset.name],
  -          validateData: {
  -            project: () => project.permits('dataset.read')
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId',
  +      component: 'FormShow',
  +      props: true,
  +      loading: 'page',
  +      key: ({ projectId, xmlFormId }) =>
  +        `/projects/${projectId}/forms/${encodeURIComponent(xmlFormId)}`,
  +      children: [
  +        asyncRoute({
  +          path: 'versions',
  +          component: 'FormVersionList',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              // Including submission.list in order to exclude Data Collectors.
  +              project: () => project.permits(['form.read', 'submission.list']),
  +              form: () => form.publishedAt != null
  +            },
  +            title: () => [i18n.t('formHead.tab.versions'), form.nameOrId]
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'submissions',
  +          alias: '',
  +          component: 'FormSubmissions',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits([
  +                'form.read',
  +                'submission.list',
  +                'submission.read'
  +              ]),
  +              form: () => form.publishedAt != null
  +            },
  +            title: () => [i18n.t('resource.submissions'), form.nameOrId],
  +            fullWidth: true
             }
  +        }),
  +        asyncRoute({
  +          path: 'public-links',
  +          component: 'PublicLinkList',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits([
  +                'form.read',
  +                'public_link.list',
  +                'public_link.create',
  +                'session.end'
  +              ]),
  +              form: () => form.publishedAt != null
  +            },
  +            title: () => [i18n.t('formHead.tab.publicAccess'), form.nameOrId]
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'settings',
  +          component: 'FormSettings',
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits([
  +                'form.read',
  +                'form.update',
  +                'form.delete'
  +              ]),
  +              form: () => form.publishedAt != null
  +            },
  +            title: () => [i18n.t('common.tab.settings'), form.nameOrId]
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'draft',
  +          component: 'FormEdit',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              project: () => project.permits([
  +                'form.read',
  +                'form.update',
  +                'form.delete',
  +                'dataset.list',
  +                'entity.list',
  +                'submission.list',
  +                'submission.read'
  +              ])
  +            },
  +            title: () => [i18n.t('formHead.tab.editForm'), form.nameOrId],
  +            fullWidth: true
  +          }
  +        })
  +      ]
  +    }),
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/submissions/:instanceId',
  +      component: 'SubmissionShow',
  +      props: true,
  +      loading: 'page',
  +      meta: {
  +        validateData: {
  +          project: () => project.permits('submission.read')
           }
  +      }
  +    }),
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/preview',
  +      component: 'FormPreview',
  +      props: (route) => ({
  +        ...route.params,
  +        draft: false
         }),
  -      asyncRoute({
  -        path: 'entities',
  -        alias: '',
  -        component: 'DatasetEntities',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          title: () => [i18n.t('resource.entities'), dataset.name],
  -          validateData: {
  -            project: () => project.permits(['dataset.read', 'entity.list'])
  -          },
  -          fullWidth: true
  -        }
  +      loading: 'page',
  +      meta: {
  +        standalone: true,
  +        title: () => [`✨ ${i18n.t('resource.formPreview')}`, form.nameOrId ?? '']
  +      }
  +    }),
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/draft/preview',
  +      name: 'FormDraftPreview',
  +      component: 'FormPreview',
  +      props: (route) => ({
  +        ...route.params,
  +        draft: true
         }),
  -      asyncRoute({
  -        path: 'settings',
  -        component: 'DatasetSettings',
  -        props: true,
  -        loading: 'tab',
  -        meta: {
  -          title: () => [i18n.t('common.tab.settings'), dataset.name],
  -          validateData: {
  -            project: () => project.permits(['dataset.read', 'dataset.update', 'entity.list'])
  +      loading: 'page',
  +      meta: {
  +        standalone: true,
  +        title: () => [`✨ ${i18n.t('resource.formPreview')}`, form.nameOrId ? `${form.nameOrId} (${i18n.t('resource.draft')})` : '']
  +      }
  +    }),
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)/entity-lists/:datasetName',
  +      component: 'DatasetShow',
  +      props: true,
  +      loading: 'page',
  +      key: ({ projectId, datasetName }) =>
  +        `/projects/${projectId}/entity-lists/${encodeURIComponent(datasetName)}`,
  +      children: [
  +        asyncRoute({
  +          path: 'properties',
  +          component: 'DatasetOverview',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            title: () => [i18n.t('resource.properties'), dataset.name],
  +            validateData: {
  +              project: () => project.permits('dataset.read')
  +            }
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'entities',
  +          alias: '',
  +          component: 'DatasetEntities',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            title: () => [i18n.t('resource.entities'), dataset.name],
  +            validateData: {
  +              project: () => project.permits(['dataset.read', 'entity.list'])
  +            },
  +            fullWidth: true
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'settings',
  +          component: 'DatasetSettings',
  +          props: true,
  +          loading: 'tab',
  +          meta: {
  +            title: () => [i18n.t('common.tab.settings'), dataset.name],
  +            validateData: {
  +              project: () => project.permits(['dataset.read', 'dataset.update', 'entity.list'])
  +            }
             }
  +        })
  +      ]
  +    }),
  +    asyncRoute({
  +      // We don't validate that :uuid is a valid UUID (and it isn't in tests), but
  +      // we do validate that it doesn't need to be URL-encoded (for example, in
  +      // requests to Backend).
  +      path: '/projects/:projectId([1-9]\\d*)/entity-lists/:datasetName/entities/:uuid([0-9a-f-]+)',
  +      component: 'EntityShow',
  +      props: true,
  +      loading: 'page',
  +      meta: {
  +        validateData: {
  +          project: () => project.permits(['dataset.read', 'entity.read'])
           }
  -      })
  -    ]
  -  }),
  -  asyncRoute({
  -    // We don't validate that :uuid is a valid UUID (and it isn't in tests), but
  -    // we do validate that it doesn't need to be URL-encoded (for example, in
  -    // requests to Backend).
  -    path: '/projects/:projectId([1-9]\\d*)/entity-lists/:datasetName/entities/:uuid([0-9a-f-]+)',
  -    component: 'EntityShow',
  -    props: true,
  -    loading: 'page',
  -    meta: {
  -      validateData: {
  -        project: () => project.permits(['dataset.read', 'entity.read'])
         }
  -    }
  -  }),
  +    }),
   
  -  asyncRoute({
  -    path: '/users',
  -    component: 'UserHome',
  -    loading: 'page',
  -    key: () => '/users',
  -    children: [
  -      asyncRoute({
  -        path: '',
  -        component: 'UserList',
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            currentUser: () => currentUser.can([
  -              'user.list',
  -              'assignment.list',
  -              'user.create',
  -              'assignment.create',
  -              'assignment.delete',
  -              'user.password.invalidate',
  -              'user.delete'
  -            ])
  -          },
  -          title: () => [i18n.t('resource.webUsers')]
  +    asyncRoute({
  +      path: '/users',
  +      component: 'UserHome',
  +      loading: 'page',
  +      key: () => '/users',
  +      children: [
  +        asyncRoute({
  +          path: '',
  +          component: 'UserList',
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              currentUser: () => currentUser.can([
  +                'user.list',
  +                'assignment.list',
  +                'user.create',
  +                'assignment.create',
  +                'assignment.delete',
  +                'user.password.invalidate',
  +                'user.delete'
  +              ])
  +            },
  +            title: () => [i18n.t('resource.webUsers')]
  +          }
  +        })
  +      ]
  +    }),
  +    asyncRoute({
  +      path: '/users/:id([1-9]\\d*)/edit',
  +      component: 'UserEdit',
  +      props: true,
  +      loading: 'page',
  +      meta: {
  +        validateData: {
  +          currentUser: () => currentUser.can(['user.read', 'user.update'])
           }
  -      })
  -    ]
  -  }),
  -  asyncRoute({
  -    path: '/users/:id([1-9]\\d*)/edit',
  -    component: 'UserEdit',
  -    props: true,
  -    loading: 'page',
  -    meta: {
  -      validateData: {
  -        currentUser: () => currentUser.can(['user.read', 'user.update'])
         }
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/account/edit',
  -    component: 'AccountEdit',
  -    loading: 'page',
  -    meta: {
  -      title: () => [i18n.t('title.editProfile')]
  -    }
  -  }),
  +    }),
  +    asyncRoute({
  +      path: '/account/edit',
  +      component: 'AccountEdit',
  +      loading: 'page',
  +      meta: {
  +        title: () => [i18n.t('title.editProfile')]
  +      }
  +    }),
   
  -  asyncRoute({
  -    path: '/system',
  -    component: 'SystemHome',
  -    loading: 'page',
  -    key: () => '/system',
  -    children: [
  -      asyncRoute({
  -        path: 'audits',
  -        component: 'AuditList',
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            currentUser: () => currentUser.can('audit.read')
  -          },
  -          title: () => [i18n.t('systemHome.tab.audits'), i18n.t('systemHome.title')],
  -          fullWidth: true
  -        }
  -      }),
  -      asyncRoute({
  -        path: 'analytics',
  -        component: 'AnalyticsList',
  -        loading: 'tab',
  -        meta: {
  -          validateData: {
  -            currentUser: () => currentUser.can([
  -              'config.read',
  -              'config.set',
  -              'analytics.read'
  -            ])
  +    asyncRoute({
  +      path: '/system',
  +      component: 'SystemHome',
  +      loading: 'page',
  +      key: () => '/system',
  +      children: [
  +        asyncRoute({
  +          path: 'audits',
  +          component: 'AuditList',
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              currentUser: () => currentUser.can('audit.read')
  +            },
  +            title: () => [i18n.t('systemHome.tab.audits'), i18n.t('systemHome.title')],
  +            fullWidth: true
  +          }
  +        }),
  +        asyncRoute({
  +          path: 'analytics',
  +          component: 'AnalyticsList',
  +          loading: 'tab',
  +          meta: {
  +            validateData: {
  +              currentUser: () => currentUser.can([
  +                'config.read',
  +                'config.set',
  +                'analytics.read'
  +              ])
  +            },
  +            title: () => [
  +              i18n.t('systemHome.tab.analytics'),
  +              i18n.t('systemHome.title')
  +            ],
  +            fullWidth: true
             },
  -          title: () => [
  -            i18n.t('systemHome.tab.analytics'),
  -            i18n.t('systemHome.title')
  -          ],
  -          fullWidth: true
  -        },
  -        beforeEnter: () => (config.showsAnalytics ? true : '/404')
  -      })
  -    ]
  -  }),
  -
  -  asyncRoute({
  -    path: '/dl/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/submissions/:instanceId/attachments/:attachmentName',
  -    component: 'Download',
  -    props: true,
  -    loading: 'page',
  -    meta: {
  -      title: () => [i18n.t('title.download')]
  -    }
  -  }),
  -
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/submissions/:instanceId/:actionType(edit)',
  -    component: 'FormSubmission',
  -    name: 'SubmissionEdit',
  -    props: true,
  -    loading: 'page',
  -    meta: {
  -      standalone: true,
  -      skipAutoLogout: true,
  -      // validateData is done inside FormSubmission component
  -      title: () => [form.nameOrId],
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/submissions/new/:offline(offline)?',
  -    component: 'FormSubmission',
  -    name: 'SubmissionNew',
  -    props: (route) => {
  -      const { offline, ...params } = route.params;
  -      return {
  -        ...params,
  -        actionType: offline === 'offline' ? 'offline' : 'new',
  -      };
  -    },
  -    loading: 'page',
  -    meta: {
  -      standalone: true,
  -      skipAutoLogout: true,
  -      // validateData is done inside FormSubmission component
  -      title: () => [form.nameOrId],
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/draft/submissions/new/:offline(offline)?',
  -    component: 'FormSubmission',
  -    name: 'DraftSubmissionNew',
  -    props: (route) => {
  -      const { offline, ...params } = route.params;
  -      return {
  -        ...params,
  -        actionType: offline === 'offline' ? 'offline' : 'new',
  -        draft: true
  -      };
  -    },
  -    loading: 'page',
  -    meta: {
  -      standalone: true,
  -      // validateData is done inside FormSubmission component
  -      title: () => [form.nameOrId],
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/f/:enketoId([a-zA-Z0-9]+)/:actionType(new|preview)',
  -    component: 'FormSubmission',
  -    name: 'EnketoRedirector',
  -    props: true,
  -    loading: 'page',
  -    meta: {
  -      standalone: true
  -    }
  -  }),
  -  asyncRoute({
  -    path: '/f/:enketoId([a-zA-Z0-9]+)/:offline(offline)?',
  -    component: 'FormSubmission',
  -    name: 'WebFormDirectLink',
  -    props: (route) => {
  -      const { offline, ...params } = route.params;
  -      return {
  -        ...params,
  -        actionType: offline === 'offline' ? 'offline' : 'public-link',
  -      };
  -    },
  -    loading: 'page',
  -    meta: {
  -      standalone: true,
  -      restoreSession: true,
  -      requireLogin: false,
  -      skipAutoLogout: true,
  -      title: () => [form.nameOrId]
  -    }
  -  }),
  +          beforeEnter: () => (config.showsAnalytics ? true : '/404')
  +        }),
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
  +      ]
  +    }),
   
  -  asyncRoute({
  -    path: '/:_(.*)',
  -    component: 'NotFound',
  -    loading: 'page',
  -    meta: {
  -      restoreSession: false,
  -      requireLogin: false,
  -      title: () => [i18n.t('title.pageNotFound')]
  -    }
  -  })
  -];
  +    asyncRoute({
  +      path: '/dl/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/submissions/:instanceId/attachments/:attachmentName',
  +      component: 'Download',
  +      props: true,
  +      loading: 'page',
  +      meta: {
  +        title: () => [i18n.t('title.download')]
  +      }
  +    }),
   
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/submissions/:instanceId/:actionType(edit)',
  +      component: 'FormSubmission',
  +      name: 'SubmissionEdit',
  +      props: true,
  +      loading: 'page',
  +      meta: {
  +        standalone: true,
  +        skipAutoLogout: true,
  +        // validateData is done inside FormSubmission component
  +        title: () => [form.nameOrId],
  +      }
  +    }),
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/submissions/new/:offline(offline)?',
  +      component: 'FormSubmission',
  +      name: 'SubmissionNew',
  +      props: (route) => {
  +        const { offline, ...params } = route.params;
  +        return {
  +          ...params,
  +          actionType: offline === 'offline' ? 'offline' : 'new',
  +        };
  +      },
  +      loading: 'page',
  +      meta: {
  +        standalone: true,
  +        skipAutoLogout: true,
  +        // validateData is done inside FormSubmission component
  +        title: () => [form.nameOrId],
  +      }
  +    }),
  +    asyncRoute({
  +      path: '/projects/:projectId([1-9]\\d*)/forms/:xmlFormId/draft/submissions/new/:offline(offline)?',
  +      component: 'FormSubmission',
  +      name: 'DraftSubmissionNew',
  +      props: (route) => {
  +        const { offline, ...params } = route.params;
  +        return {
  +          ...params,
  +          actionType: offline === 'offline' ? 'offline' : 'new',
  +          draft: true
  +        };
  +      },
  +      loading: 'page',
  +      meta: {
  +        standalone: true,
  +        // validateData is done inside FormSubmission component
  +        title: () => [form.nameOrId],
  +      }
  +    }),
  +    asyncRoute({
  +      path: '/f/:enketoId([a-zA-Z0-9]+)/:actionType(new|preview)',
  +      component: 'FormSubmission',
  +      name: 'EnketoRedirector',
  +      props: true,
  +      loading: 'page',
  +      meta: {
  +        standalone: true
  +      }
  +    }),
  +    asyncRoute({
  +      path: '/f/:enketoId([a-zA-Z0-9]+)/:offline(offline)?',
  +      component: 'FormSubmission',
  +      name: 'WebFormDirectLink',
  +      props: (route) => {
  +        const { offline, ...params } = route.params;
  +        return {
  +          ...params,
  +          actionType: offline === 'offline' ? 'offline' : 'public-link',
  +        };
  +      },
  +      loading: 'page',
  +      meta: {
  +        standalone: true,
  +        restoreSession: true,
  +        requireLogin: false,
  +        skipAutoLogout: true,
  +        title: () => [form.nameOrId]
  +      }
  +    }),
   
  +    asyncRoute({
  +      path: '/:_(.*)',
  +      component: 'NotFound',
  +      loading: 'page',
  +      meta: {
  +        restoreSession: false,
  +        requireLogin: false,
  +        title: () => [i18n.t('title.pageNotFound')]
  +      }
  +    })
  +  ];
   
  -////////////////////////////////////////////////////////////////////////////////
  -// TRAVERSE ROUTES
   
  -const routesByName = new Map();
  -{
  -  // Normalizes the values of meta fields, including by setting defaults.
  -  const normalizeMeta = (meta) => ({
  -    restoreSession: true,
  -    requireLogin: true,
  -    requireAnonymity: false,
  -    preserveData: [],
  -    fullWidth: false,
  -    standalone: false,
  -    skipAutoLogout: false,
  -    ...meta,
  -    validateData: meta == null || meta.validateData == null
  -      ? []
  -      : Object.entries(meta.validateData)
  -        .map(([name, validator]) => [requestData[name], validator])
  -  });
   
  -  const stack = [...routes];
  -  while (stack.length !== 0) {
  -    const route = stack.pop();
  -    if (route.children != null) {
  -      if (route.meta == null) route.meta = {};
  +  ////////////////////////////////////////////////////////////////////////////////
  +  // TRAVERSE ROUTES
   
  -      for (const child of route.children)
  -        stack.push(child);
  -    } else {
  -      route.meta = normalizeMeta(route.meta);
  -      routesByName.set(route.name, route);
  +  const routesByName = new Map();
  +  {
  +    // Normalizes the values of meta fields, including by setting defaults.
  +    const normalizeMeta = (meta) => ({
  +      restoreSession: true,
  +      requireLogin: true,
  +      requireAnonymity: false,
  +      preserveData: [],
  +      fullWidth: false,
  +      standalone: false,
  +      skipAutoLogout: false,
  +      ...meta,
  +      validateData: meta == null || meta.validateData == null
  +        ? []
  +        : Object.entries(meta.validateData)
  +          .map(([name, validator]) => [requestData[name], validator])
  +    });
  +
  +    const stack = [...routes];
  +    while (stack.length !== 0) {
  +      const route = stack.pop();
  +      if (route.children != null) {
  +        if (route.meta == null) route.meta = {};
  +
  +        for (const child of route.children)
  +          stack.push(child);
  +      } else {
  +        route.meta = normalizeMeta(route.meta);
  +        routesByName.set(route.name, route);
  +      }
       }
     }
  -}
     /* eslint-enable indent */ // TODO/vue3
   
   
  ```

- Date: 2025-12-21
  File: src/util/load-async.js
  Change summary: FieldKeyList loads vg-list; added VgSettings loader.
  Reason: Use VG UI components.
  Risk/notes: Medium; swaps component implementation.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/util/load-async.js b/src/util/load-async.js
  index d804ff66..9ea21cfc 100644
  --- a/src/util/load-async.js
  +++ b/src/util/load-async.js
  @@ -101,7 +101,7 @@ const loaders = new Map()
     )))
     .set('FieldKeyList', loader(() => import(
       /* webpackChunkName: "component-field-key-list" */
  -    '../components/field-key/list.vue'
  +    '../components/field-key/vg-list.vue'
     )))
     .set('FormEdit', loader(() => import(
       /* webpackChunkName: "component-form-edit" */
  @@ -201,6 +201,10 @@ const loaders = new Map()
       /* webpackChunkName: "component-system-home" */
       '../components/system/home.vue'
     )))
  +  .set('VgSettings', loader(() => import(
  +    /* webpackChunkName: "component-vg-settings" */
  +    '../components/system/vg-settings.vue'
  +  )))
     .set('UserEdit', loader(() => import(
       /* webpackChunkName: "component-user-edit" */
       '../components/user/edit.vue'
  ```

- Date: 2025-12-21
  File: src/util/request.js
  Change summary: Added app-user auth API paths (login/update/reset/revoke/active).
  Reason: Support VG app-user auth endpoints.
  Risk/notes: Low; adds helpers only.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/src/util/request.js b/src/util/request.js
  index 44cc2fbe..f42a03b9 100644
  --- a/src/util/request.js
  +++ b/src/util/request.js
  @@ -187,6 +187,11 @@ export const apiPaths = {
     entityVersions: entityPath('/versions'),
     entityRestore: entityPath('/restore'),
     fieldKeys: projectPath('/app-users'),
  +  fieldKeyLogin: (projectId) => `/v1/projects/${projectId}/app-users/login`,
  +  fieldKeyUpdate: (projectId, id) => `/v1/projects/${projectId}/app-users/${id}`,
  +  fieldKeyResetPassword: (projectId, id) => `/v1/projects/${projectId}/app-users/${id}/password/reset`,
  +  fieldKeyRevoke: (projectId, id) => `/v1/projects/${projectId}/app-users/${id}/revoke-admin`,
  +  fieldKeyActive: (projectId, id) => `/v1/projects/${projectId}/app-users/${id}/active`,
     serverUrlForFieldKey: (token, projectId) =>
       `/v1/key/${token}/projects/${projectId}`,
     audits: (query) => `/v1/audits${queryString(query)}`,
  ```

- Date: 2025-12-21
  File: vite.config.js
  Change summary: host=true and allowedHosts includes central.local.
  Reason: Allow dev access via central.local.
  Risk/notes: Low; dev-only config.
  Related commits/PRs: vg-work history (see client/docs/vg_client_changes.md)
  Diff:
  ```diff
  diff --git a/vite.config.js b/vite.config.js
  index e7f543aa..f91d5b11 100644
  --- a/vite.config.js
  +++ b/vite.config.js
  @@ -30,7 +30,9 @@ const proxyPaths = [
     '/version.txt'
   ];
   const devServer = {
  +  host: true,
     port: 8989,
  +  allowedHosts: ['central.local'],
     proxy: Object.fromEntries(proxyPaths.map(path => [path, 'http://localhost:8686'])),
     // Because we proxy to nginx, which itself proxies to Backend and other
     // things, the dev server doesn't need to allow CORS. CORS is already limited
  ```
