# VG Core Server Edits (Required Log)

This log must include only VG fork modifications and exclude upstream master changes introduced by rebases or merges.

This file must document every edit made to upstream core server files
in `getodk/central-backend`. Use it to keep rebases manageable.

## Log Format (one entry per change)

- Date:
- File:
- Change summary:
- Reason:
- Risk/notes:
- Related commits/PRs:

## Entries

- Date: 2026-01-01
  File: lib/resources/sessions.js
  Change summary: Log failed web login attempts with normalized identifiers and metadata.
  Reason: Add audit visibility for /v1/sessions failures.
  Risk/notes: Low; audit-only change.
  Related commits/PRs: vg-work history

- Date: 2026-01-01
  File: lib/model/query/audits.js
  Change summary: Include failed web login and lockout audits in the user action filter.
  Reason: Ensure audit filtering includes login failure/lockout events.
  Risk/notes: Low; filter expansion.
  Related commits/PRs: vg-work history

- Date: 2026-01-01
  File: lib/resources/sessions.js
  Change summary: Enforce web login lockout based on recent failures with audit-backed tracking.
  Reason: Add rate limiting/lockout to /v1/sessions.
  Risk/notes: Medium; auth flow change.
  Related commits/PRs: vg-work history

- Date: 2026-01-01
  File: lib/model/query/audits.js
  Change summary: Add queries for recent web login failures and lockouts.
  Reason: Support web login lockout checks using audit data.
  Risk/notes: Low; query-only change.
  Related commits/PRs: vg-work history

- Date: 2026-01-01
  File: lib/model/query/users.js
  Change summary: Add helper to fetch any user password hash for timing normalization.
  Reason: Support dummy password verification for missing emails.
  Risk/notes: Low; query-only change.
  Related commits/PRs: vg-work history

- Date: 2026-01-01
  File: lib/resources/sessions.js
  Change summary: Make web login lockout duration configurable via vg_settings.
  Reason: Allow system-level control of web user lockout duration.
  Risk/notes: Low; configuration read.
  Related commits/PRs: vg-work history

- Date: 2025-12-21
  File: docs/database.md
  Change summary: Documented VG auth tables and settings.
  Reason: Track vg_* schema additions.
  Risk/notes: Low.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/docs/database.md b/docs/database.md
  index 299498f5..f49d104f 100644
  --- a/docs/database.md
  +++ b/docs/database.md
  @@ -162,4 +162,5 @@ This area of the database deals with the users, their access rights and audit lo
   These are few stand-alone tables. 
   
   - `configs` table hold different application configurations related analytics, backups, etc
  +- `vg_settings` stores vg-specific key/value configuration such as `vg_app_user_session_ttl_days` (default seeded to 3 days for app-user session expiry).
   - `knex_migrations` and `knex_migrations_lock` are used internally by Knex.js for keeping database migrations history.
  ```

- Date: 2025-12-21
  File: lib/http/service.js
  Change summary: Wired vg auth resources and auth behavior.
  Reason: Expose new VG endpoints.
  Risk/notes: Medium; core request routing.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/http/service.js b/lib/http/service.js
  index fa114174..c83c8a80 100644
  --- a/lib/http/service.js
  +++ b/lib/http/service.js
  @@ -98,6 +98,7 @@ module.exports = (container) => {
     require('../resources/forms')(service, endpoint, anonymousEndpoint);
     require('../resources/users')(service, endpoint, anonymousEndpoint);
     require('../resources/sessions')(service, endpoint, anonymousEndpoint);
  +  require('../resources/vg-app-user-auth')(service, endpoint, anonymousEndpoint);
     require('../resources/geo-extracts')(service, endpoint);
     require('../resources/submissions')(service, endpoint, anonymousEndpoint);
     require('../resources/config')(service, endpoint);
  @@ -159,4 +160,3 @@ module.exports = (container) => {
     return service;
   
   };
  -
  ```

- Date: 2025-12-21
  File: lib/model/container.js
  Change summary: Container bindings updated for VG auth components.
  Reason: Register vg auth domain/query resources.
  Risk/notes: Low.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/container.js b/lib/model/container.js
  index e2c209fd..04055d75 100644
  --- a/lib/model/container.js
  +++ b/lib/model/container.js
  @@ -113,10 +113,10 @@ const withDefaults = (base, queries) => {
       Entities: require('./query/entities'),
       UserPreferences: require('./query/user-preferences'),
       GeoExtracts: require('./query/geo-extracts'),
  +    VgAppUserAuth: require('./query/vg-app-user-auth'),
     };
   
     return injector(base, mergeRight(defaultQueries, queries));
   };
   
   module.exports = { queryModuleBuilder, injector, withDefaults };
  -
  ```

- Date: 2025-12-21
  File: lib/model/query/actors.js
  Change summary: Actor query updates for VG app-user auth metadata.
  Reason: Support username/phone fields and active flags.
  Risk/notes: Medium.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/query/actors.js b/lib/model/query/actors.js
  index 7cdb49f3..4935b7f6 100644
  --- a/lib/model/query/actors.js
  +++ b/lib/model/query/actors.js
  @@ -48,5 +48,7 @@ const getById = (id) => ({ maybeOne }) =>
     maybeOne(sql`select * from actors where id=${id} and "deletedAt" is null`)
       .then(map(construct(Actor)));
   
  -module.exports = { create, createSubtype, consume, _del, del, getById };
  +const updateDisplayName = (actorId, displayName) => ({ run }) =>
  +  run(sql`UPDATE actors SET "displayName"=${displayName} WHERE id=${actorId}`);
   
  +module.exports = { create, createSubtype, consume, _del, del, getById, updateDisplayName };
  ```

- Date: 2025-12-21
  File: lib/model/query/field-keys.js
  Change summary: Field key queries updated for VG auth and active status.
  Reason: Support short-lived token model and list behavior.
  Risk/notes: Medium.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/query/field-keys.js b/lib/model/query/field-keys.js
  index ddaf98e3..b2abb55c 100644
  --- a/lib/model/query/field-keys.js
  +++ b/lib/model/query/field-keys.js
  @@ -20,12 +20,29 @@ const create = (fk, project) => ({ Actors, Sessions }) =>
   create.audit = (result) => (log) => log('field_key.create', result.actor);
   create.audit.withResult = true;
   
  -const _get = extender(FieldKey, Actor, Frame.define('token', readable))(Actor.alias('created_by', 'createdBy'), Frame.define('lastUsed', readable))((fields, extend, options) => sql`
  +// createWithoutSession lets us create a field key without auto-issuing
  +//  the legacy 9999-year session. The vg flow needs to create the actor
  +//  field_key row, attach the vg auth record, and then issue a short-
  +//  lived session only after a successful login/password check. Using the
  +//  existing create would still mint the long-lived token, which we want
  +//  to avoid.
  +
  +const createWithoutSession = (fk, project) => ({ Actors }) =>
  +  Actors.createSubtype(fk.with({ projectId: project.id }), project);
  +
  +const _get = extender(FieldKey, Actor, Frame.define('token', readable), Frame.define('active', readable, 'username', readable, 'phone', readable).into('activeStatus'))(Actor.alias('created_by', 'createdBy'), Frame.define('lastUsed', readable))((fields, extend, options) => sql`
   select ${fields} from field_keys
     join actors on field_keys."actorId"=actors.id
  -  left outer join sessions on field_keys."actorId"=sessions."actorId"
  -  ${extend|| sql`join actors as created_by on field_keys."createdBy"=created_by.id`}
  -  ${extend|| sql`left outer join
  +  left outer join lateral (
  +    select token, "actorId"
  +      from sessions
  +     where sessions."actorId" = field_keys."actorId"
  +     order by "createdAt" desc
  +     limit 1
  +  ) as sessions on true
  +  left outer join (select "actorId", coalesce(vg_active, true) as active, vg_username as username, vg_phone as phone from vg_field_key_auth) as vg_auth on field_keys."actorId"=vg_auth."actorId"
  +  ${extend || sql`join actors as created_by on field_keys."createdBy"=created_by.id`}
  +  ${extend || sql`left outer join
       (select "actorId", max("loggedAt") as "lastUsed" from audits
         where action='submission.create'
         group by "actorId") as last_usage
  @@ -39,5 +56,4 @@ const getAllForProject = (project, options = QueryOptions.none) => ({ all }) =>
   const getByProjectAndActorId = (projectId, actorId, options = QueryOptions.none) => ({ maybeOne }) =>
     _get(maybeOne, options.withCondition({ projectId, 'field_keys.actorId': actorId }));
   
  -module.exports = { create, getAllForProject, getByProjectAndActorId };
  -
  +module.exports = { create, createWithoutSession, getAllForProject, getByProjectAndActorId };
  ```

- Date: 2025-12-21
  File: lib/model/query/sessions.js
  Change summary: Session logic updated for TTL/cap and VG auth.
  Reason: Enforce session limits for app-user logins.
  Risk/notes: High; auth/session integrity.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/query/sessions.js b/lib/model/query/sessions.js
  index 1cc7ca48..0275bb09 100644
  --- a/lib/model/query/sessions.js
  +++ b/lib/model/query/sessions.js
  @@ -42,13 +42,27 @@ const _unjoiner = unjoiner(Session, Actor);
   const getByBearerToken = (token) => ({ maybeOne }) => (isValidToken(token) ? maybeOne(sql`
   select ${_unjoiner.fields} from sessions
   join actors on actors.id=sessions."actorId"
  -where token=${token} and sessions."expiresAt" > now()`)
  +left join vg_field_key_auth on vg_field_key_auth."actorId"=sessions."actorId"
  +where token=${token} and sessions."expiresAt" > now()
  +  and (actors.type <> 'field_key' or coalesce(vg_field_key_auth.vg_active, true) = true)`)
     .then(map(_unjoiner)) : Promise.resolve(Option.none()));
   
   const terminateByActorId = (actorId, current = undefined) => ({ run }) =>
     run(sql`DELETE FROM sessions WHERE "actorId"=${actorId}
   ${current == null ? sql`` : sql`AND token <> ${current}`}`);
   
  +const trimByActorId = (actorId, limit) => ({ run }) =>
  +  run(sql`
  +    DELETE FROM sessions
  +    WHERE "actorId"=${actorId}
  +      AND token NOT IN (
  +        SELECT token FROM sessions
  +        WHERE "actorId"=${actorId}
  +        ORDER BY "createdAt" DESC
  +        LIMIT ${limit}
  +      )
  +  `);
  +
   const terminate = (session) => ({ run }) =>
     run(sql`delete from sessions where token=${session.token}`);
   
  @@ -62,5 +76,4 @@ terminate.audit = (session) => (log) => {
   const reap = () => ({ run }) =>
     run(sql`delete from sessions where "expiresAt" < now()`);
   
  -module.exports = { create, getByBearerToken, terminateByActorId, terminate, reap };
  -
  +module.exports = { create, getByBearerToken, terminateByActorId, trimByActorId, terminate, reap };
  ```

- Date: 2025-12-30
  File: lib/model/query/sessions.js
  Change summary: Require vg_field_key_auth presence to authenticate field_key sessions.
  Reason: Block legacy long-lived field-key tokens without VG auth records.
  Risk/notes: High; app-user authentication behavior.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/query/sessions.js b/lib/model/query/sessions.js
  index 0275bb09..5e8a7d2f 100644
  --- a/lib/model/query/sessions.js
  +++ b/lib/model/query/sessions.js
  @@ -44,7 +44,7 @@ const getByBearerToken = (token) => ({ maybeOne }) => (isValidToken(token) ? maybeOne(sql`
   select ${_unjoiner.fields} from sessions
   join actors on actors.id=sessions."actorId"
   left join vg_field_key_auth on vg_field_key_auth."actorId"=sessions."actorId"
   where token=${token} and sessions."expiresAt" > now()
  -  and (actors.type <> 'field_key' or coalesce(vg_field_key_auth.vg_active, true) = true)`)
  +  and (actors.type <> 'field_key' or (vg_field_key_auth."actorId" is not null and vg_field_key_auth.vg_active = true))`)
  ```
- Date: 2025-12-21
  File: lib/resources/app-users.js
  Change summary: App user API updated to support new fields and behavior.
  Reason: Add username/phone, active status, and admin actions.
  Risk/notes: Medium.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/resources/app-users.js b/lib/resources/app-users.js
  index 98b5674b..a8dc78af 100644
  --- a/lib/resources/app-users.js
  +++ b/lib/resources/app-users.js
  @@ -7,9 +7,9 @@
   // including this file, may be copied, modified, propagated, or distributed
   // except according to the terms contained in the LICENSE file.
   
  -const { FieldKey } = require('../model/frames');
   const { getOrNotFound } = require('../util/promise');
   const { success } = require('../util/http');
  +const vgAuth = require('../domain/vg-app-user-auth');
   
   module.exports = (service, endpoint) => {
   
  @@ -17,17 +17,36 @@ module.exports = (service, endpoint) => {
       Projects.getById(params.projectId)
         .then(getOrNotFound)
         .then((project) => auth.canOrReject('field_key.list', project))
  -      .then((project) => FieldKeys.getAllForProject(project, queryOptions))));
  +      .then((project) => FieldKeys.getAllForProject(project, queryOptions))
  +      // VG: do not expose active session tokens in listings.
  +      .then((keys) => keys.map((fk) => ({ ...fk.forApi(), token: null, session: undefined, active: fk.aux.activeStatus?.active, username: fk.aux.activeStatus?.username, phone: fk.aux.activeStatus?.phone })))));
   
  -  service.post('/projects/:projectId/app-users', endpoint(({ FieldKeys, Projects }, { auth, body, params }) =>
  +  service.post('/projects/:projectId/app-users', endpoint(({ FieldKeys, Projects, VgAppUserAuth, Sessions, Audits }, { auth, body, params }) =>
       Projects.getById(params.projectId)
         .then(getOrNotFound)
  -      .then((project) => auth.canOrReject('field_key.create', project))
  -      .then((project) => {
  -        const fk = FieldKey.fromApi(body)
  -          .with({ createdBy: auth.actor.map((actor) => actor.id).orNull() });
  -        return FieldKeys.create(fk, project);
  -      })));
  +      .then((project) => auth.canOrReject('field_key.create', project)
  +        .then(() => vgAuth.createAppUser({ FieldKeys, VgAppUserAuth, Sessions, Audits }, project, body, auth.actor.map((actor) => actor.id).orNull())))));
  +
  +  service.patch('/projects/:projectId/app-users/:id', endpoint(async ({ Actors, FieldKeys, Projects, VgAppUserAuth }, { auth, body, params }) => {
  +    const project = await Projects.getById(params.projectId).then(getOrNotFound);
  +    const canUpdate = await auth.can('field_key.update', project);
  +    if (!canUpdate) await auth.canOrReject('field_key.create', project);
  +    const fk = await FieldKeys.getByProjectAndActorId(project.id, params.id).then(getOrNotFound);
  +
  +    await vgAuth.updateAppUser({ Actors, VgAppUserAuth, context: { auth } }, fk.actorId, project.id, body);
  +
  +    // Return the latest data (no token, include phone/active/username).
  +    const refreshed = await FieldKeys.getByProjectAndActorId(project.id, params.id).then(getOrNotFound);
  +    const activeStatus = refreshed.aux.activeStatus || {};
  +    return {
  +      ...refreshed.forApi(),
  +      token: null,
  +      session: undefined,
  +      active: activeStatus.active,
  +      username: activeStatus.username,
  +      phone: activeStatus.phone
  +    };
  +  }));
   
     service.delete('/projects/:projectId/app-users/:id', endpoint(({ Actors, FieldKeys, Projects }, { auth, params }) =>
       Projects.getById(params.projectId)
  @@ -39,4 +58,3 @@ module.exports = (service, endpoint) => {
         .then(success)));
   
   };
  -
  ```

- Date: 2025-12-21
  File: lib/util/problem.js
  Change summary: Added VG-specific problem codes/messages.
  Reason: Provide clear errors for app-user auth flows.
  Risk/notes: Low.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/util/problem.js b/lib/util/problem.js
  index 1611a15f..6cda4a86 100644
  --- a/lib/util/problem.js
  +++ b/lib/util/problem.js
  @@ -99,6 +99,8 @@ const problems = {
   
       expectedDeprecation: problem(400.19, () => 'This PUT endpoint expects a deprecatedID metadata tag pointing at the current version instanceID. I cannot find that tag in your request.'),
   
  +    passwordWeak: problem(400.20, () => 'The password provided does not meet the policy requirements.'),
  +
       passwordTooShort: problem(400.21, () => 'The password or passphrase provided does not meet the required length.'),
   
       valueOutOfRangeForType: problem(400.22, ({ value, type }) => `Provided value '${value}' is out of range for type '${type}'`),
  ```

- Date: 2025-12-21
  File: lib/http/service.js
  Change summary: Registered vg telemetry resource routes.
  Reason: Expose app-user telemetry endpoints.
  Risk/notes: Low; routing only.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/http/service.js b/lib/http/service.js
  index c83c8a80..e350a390 100644
  --- a/lib/http/service.js
  +++ b/lib/http/service.js
  @@ -98,6 +98,7 @@ module.exports = (container) => {
     require('../resources/users')(service, endpoint, anonymousEndpoint);
     require('../resources/sessions')(service, endpoint, anonymousEndpoint);
     require('../resources/vg-app-user-auth')(service, endpoint, anonymousEndpoint);
  +  require('../resources/vg-telemetry')(service, endpoint);
     require('../resources/geo-extracts')(service, endpoint);
  ```

- Date: 2025-12-21
  File: lib/model/container.js
  Change summary: Registered VgTelemetry query module.
  Reason: Provide DB access for app-user telemetry.
  Risk/notes: Low.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/container.js b/lib/model/container.js
  index 04055d75..c2a52b62 100644
  --- a/lib/model/container.js
  +++ b/lib/model/container.js
  @@ -114,6 +114,7 @@ const withDefaults = (base, queries) => {
       UserPreferences: require('./query/user-preferences'),
       GeoExtracts: require('./query/geo-extracts'),
       VgAppUserAuth: require('./query/vg-app-user-auth'),
  +    VgTelemetry: require('./query/vg-telemetry'),
     };
  ```

- Date: 2025-12-22
  File: lib/model/query/vg-telemetry.js
  Change summary: Add total_count window field for telemetry pagination.
  Reason: Provide total count for client pagination while keeping array response.
  Risk/notes: Low; adds window aggregate to telemetry list query.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/query/vg-telemetry.js b/lib/model/query/vg-telemetry.js
  index 6da94b2f..a9d3d1b2 100644
  --- a/lib/model/query/vg-telemetry.js
  +++ b/lib/model/query/vg-telemetry.js
  @@ -50,6 +50,7 @@ const getTelemetry = (filters = {}, options = QueryOptions.none) => ({ all }) =>
     all(sql`
       SELECT
  +      count(*) OVER () AS total_count,
         t.id,
         t."actorId" AS "appUserId",
         fk."projectId",
  ```

- Date: 2025-12-22
  File: lib/resources/vg-telemetry.js
  Change summary: Emit X-Total-Count header for telemetry listings.
  Reason: Support client-side pagination with total counts.
  Risk/notes: Low; response header added, body unchanged.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/resources/vg-telemetry.js b/lib/resources/vg-telemetry.js
  index 0afbb5a8..c1ff8bb4 100644
  --- a/lib/resources/vg-telemetry.js
  +++ b/lib/resources/vg-telemetry.js
  @@ -62,7 +62,7 @@ module.exports = (service, endpoint) => {
 
     // Admin telemetry listing with filters.
     service.get('/system/app-users/telemetry', endpoint(
  -    ({ VgTelemetry }, { auth, queryOptions }) =>
  +    ({ VgTelemetry }, { auth, queryOptions }, __, response) =>
         auth.canOrReject('config.read', Config.species)
           .then(() => {
             const options = queryOptions.allowArgs('projectId', 'deviceId', 'appUserId', 'dateFrom', 'dateTo');
  @@ -80,7 +80,13 @@ module.exports = (service, endpoint) => {
 
             return VgTelemetry.getTelemetry(filters, options);
           })
  -        .then((rows) => rows.map((row) => ({
  +        .then((rows) => {
  +          const total = rows.length !== 0 && Number.isFinite(Number(rows[0].total_count))
  +            ? Number(rows[0].total_count)
  +            : rows.length;
  +          response.set('X-Total-Count', total);
  +          return rows.map((row) => ({
             id: row.id,
             appUserId: row.appUserId,
             projectId: row.projectId,
  @@ -92,6 +98,7 @@ module.exports = (service, endpoint) => {
             deviceDateTime: row.device_date_time,
             dateTime: row.received_at,
             location: mapLocation(row)
  -        })))
  +          }));
  +        })
     ));
   };
  ```

- Date: 2025-12-22
  File: lib/model/query/vg-app-user-auth.js
  Change summary: Add paging and total_count support for app-user session listing.
  Reason: Enable pagination for login history in the client.
  Risk/notes: Low; adds window aggregate and paging to session list query.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/query/vg-app-user-auth.js b/lib/model/query/vg-app-user-auth.js
  index 648adf3b..63ef3c77 100644
  --- a/lib/model/query/vg-app-user-auth.js
  +++ b/lib/model/query/vg-app-user-auth.js
  @@ -1,6 +1,6 @@
   // Namespaced vg app-user auth queries and helpers.
   const { sql } = require('slonik');
   const { Frame, readable, table, embedded, into } = require('../frame');
   const { Actor } = require('../frames');
  -const { unjoiner } = require('../../util/db');
  +const { unjoiner, page, QueryOptions } = require('../../util/db');
  @@ -92,8 +92,10 @@ const recordSession = ({ token, actorId, ip = null, userAgent = null, deviceId =
           comments = EXCLUDED.comments
   `);
 
  -const getActiveSessionsByActorId = (actorId) => ({ all }) =>
  +const getActiveSessionsByActorId = (actorId, options = QueryOptions.none) => ({ all }) =>
     all(sql`
       SELECT
  +      count(*) OVER () AS total_count,
         s.token,
         s."createdAt",
         s."expiresAt",
  @@ -105,6 +107,7 @@ const getActiveSessionsByActorId = (actorId) => ({ all }) =>
     FROM sessions s
     JOIN vg_app_user_sessions v ON v.token = s.token
     WHERE s."actorId"=${actorId}
     ORDER BY s."createdAt" DESC
  +  ${page(options)}
   `);
  ```

- Date: 2025-12-22
  File: lib/domain/vg-app-user-auth.js
  Change summary: Pass paging options into app-user session listing.
  Reason: Wire query options through to model layer for pagination.
  Risk/notes: Low; method signature updated.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/domain/vg-app-user-auth.js b/lib/domain/vg-app-user-auth.js
  index 1d5060bb..9d4bf1ed 100644
  --- a/lib/domain/vg-app-user-auth.js
  +++ b/lib/domain/vg-app-user-auth.js
  @@ -216,9 +216,9 @@ const clearLockout = async (container, payload) => {
     return true;
   };
 
  -const listSessions = async (container, actorId) => {
  +const listSessions = async (container, actorId, options) => {
     const { VgAppUserAuth } = container;
  -  return VgAppUserAuth.getActiveSessionsByActorId(actorId);
  +  return VgAppUserAuth.getActiveSessionsByActorId(actorId, options);
   };
  ```

- Date: 2025-12-22
  File: lib/resources/vg-app-user-auth.js
  Change summary: Add X-Total-Count header and paging for app-user sessions.
  Reason: Support login history pagination in the client.
  Risk/notes: Low; response header added, body unchanged.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/resources/vg-app-user-auth.js b/lib/resources/vg-app-user-auth.js
  index 7fb5f8fb..0f2c1c48 100644
  --- a/lib/resources/vg-app-user-auth.js
  +++ b/lib/resources/vg-app-user-auth.js
  @@ -82,7 +82,7 @@ module.exports = (service, endpoint, anonymousEndpoint) => {
 
     // List active app-user sessions (admin/manager).
     service.get('/projects/:projectId/app-users/:id/sessions', endpoint(
  -    ({ Projects, FieldKeys, VgAppUserAuth }, { auth, params }) =>
  +    ({ Projects, FieldKeys, VgAppUserAuth }, { auth, params, queryOptions }, __, response) =>
         Projects.getById(params.projectId)
           .then(getOrNotFound)
           .then((project) => auth.canOrReject('field_key.list', project)
             .then(() => FieldKeys.getByProjectAndActorId(project.id, params.id)))
           .then(getOrNotFound)
  -        .then((fk) => vgAuth.listSessions({ VgAppUserAuth }, fk.actor.id))
  -        .then((sessions) => sessions.map((s) => ({
  +        .then((fk) => vgAuth.listSessions({ VgAppUserAuth }, fk.actor.id, queryOptions))
  +        .then((sessions) => {
  +          const total = sessions.length !== 0 && Number.isFinite(Number(sessions[0].total_count))
  +            ? Number(sessions[0].total_count)
  +            : sessions.length;
  +          response.set('X-Total-Count', total);
  +          return sessions.map((s) => ({
             id: s.id,
             createdAt: s.createdAt,
             expiresAt: s.expiresAt,
             ip: s.ip,
             userAgent: s.user_agent,
             deviceId: s.device_id,
             comments: s.comments
  -        })))
  +          }));
  +        })
     ));
  ```

- Date: 2025-12-22
  File: lib/model/query/vg-app-user-auth.js
  Change summary: Add project-scoped session listing with filters and paging.
  Reason: Support project-level login history UI with user/date filters.
  Risk/notes: Low; adds query and window aggregate.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/query/vg-app-user-auth.js b/lib/model/query/vg-app-user-auth.js
  index 63ef3c77..52c9ce8b 100644
  --- a/lib/model/query/vg-app-user-auth.js
  +++ b/lib/model/query/vg-app-user-auth.js
  @@ -108,6 +108,30 @@ const getActiveSessionsByActorId = (actorId, options = QueryOptions.none) => ({
      ORDER BY s."createdAt" DESC
      ${page(options)}
    `);
  +
  +const projectSessionFilterer = (filters) => {
  +  const conditions = [];
  +  if (filters.projectId != null) conditions.push(sql`fk."projectId"=${filters.projectId}`);
  +  if (filters.appUserId != null) conditions.push(sql`s."actorId"=${filters.appUserId}`);
  +  if (filters.dateFrom != null) conditions.push(sql`s."createdAt" >= ${filters.dateFrom}`);
  +  if (filters.dateTo != null) conditions.push(sql`s."createdAt" <= ${filters.dateTo}`);
  +  return (conditions.length === 0) ? sql`true` : sql.join(conditions, sql` and `);
  +};
  +
  +const getActiveSessionsByProject = (filters = {}, options = QueryOptions.none) => ({ all }) =>
  +  all(sql`
  +    SELECT
  +      count(*) OVER () AS total_count,
  +      s."actorId" AS "appUserId",
  +      s."createdAt",
  +      s."expiresAt",
  +      v.id,
  +      v.ip,
  +      v.user_agent,
  +      v.device_id,
  +      v.comments
  +    FROM sessions s
  +    JOIN vg_app_user_sessions v ON v.token = s.token
  +    JOIN field_keys fk ON fk."actorId" = s."actorId"
  +    WHERE ${projectSessionFilterer(filters)}
  +    ORDER BY s."createdAt" DESC
  +    ${page(options)}
  +  `);
  ```

- Date: 2025-12-22
  File: lib/domain/vg-app-user-auth.js
  Change summary: Add listProjectSessions domain method.
  Reason: Provide a domain entry point for project-level session listing.
  Risk/notes: Low; method wrapper only.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/domain/vg-app-user-auth.js b/lib/domain/vg-app-user-auth.js
  index 9d4bf1ed..0f7d0a3c 100644
  --- a/lib/domain/vg-app-user-auth.js
  +++ b/lib/domain/vg-app-user-auth.js
  @@ -220,6 +220,11 @@ const listSessions = async (container, actorId, options) => {
     const { VgAppUserAuth } = container;
     return VgAppUserAuth.getActiveSessionsByActorId(actorId, options);
   };
  +
  +const listProjectSessions = async (container, filters, options) => {
  +  const { VgAppUserAuth } = container;
  +  return VgAppUserAuth.getActiveSessionsByProject(filters, options);
  +};
  @@ -232,6 +237,7 @@ module.exports = {
     revokeSessions,
     setActive,
     clearLockout,
     listSessions,
  +  listProjectSessions
   };
  ```

- Date: 2025-12-22
  File: lib/resources/vg-app-user-auth.js
  Change summary: Add project-level sessions listing endpoint with filters.
  Reason: Support project login history tab with user/date filters and paging.
  Risk/notes: Low; adds new GET endpoint and header.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/resources/vg-app-user-auth.js b/lib/resources/vg-app-user-auth.js
  index 0f2c1c48..f8a0c24b 100644
  --- a/lib/resources/vg-app-user-auth.js
  +++ b/lib/resources/vg-app-user-auth.js
  @@ -12,6 +12,20 @@ module.exports = (service, endpoint, anonymousEndpoint) => {
       if (!Number.isFinite(num) || !Number.isInteger(num) || num <= 0)
         throw Problem.user.invalidDataTypeOfParameter({ field, expected: 'positive integer' });
       return num;
     };
  +  const parseIntParam = (value, field) => {
  +    if (value == null) return null;
  +    const num = Number(value);
  +    if (!Number.isFinite(num) || !Number.isInteger(num))
  +      throw Problem.user.invalidDataTypeOfParameter({ field, expected: 'integer' });
  +    return num;
  +  };
  +  const parseDateParam = (value, field) => {
  +    if (value == null) return null;
  +    const parsed = new Date(value);
  +    if (Number.isNaN(parsed.getTime()))
  +      throw Problem.user.invalidDataTypeOfParameter({ field, expected: 'ISO datetime' });
  +    return parsed;
  +  };
  @@ -108,6 +122,38 @@ module.exports = (service, endpoint, anonymousEndpoint) => {
           }));
         })
     ));
  +
  +  // List active app-user sessions for a project (admin/manager).
  +  service.get('/projects/:projectId/app-users/sessions', endpoint(
  +    ({ Projects, VgAppUserAuth }, { auth, params, queryOptions }, __, response) =>
  +      Projects.getById(params.projectId)
  +        .then(getOrNotFound)
  +        .then((project) => auth.canOrReject('field_key.list', project))
  +        .then(() => {
  +          const options = queryOptions.allowArgs('appUserId', 'dateFrom', 'dateTo');
  +          const args = options.args || {};
  +          const filters = {
  +            projectId: parseIntParam(params.projectId, 'projectId'),
  +            appUserId: parseIntParam(args.appUserId, 'appUserId'),
  +            dateFrom: parseDateParam(args.dateFrom, 'dateFrom'),
  +            dateTo: parseDateParam(args.dateTo, 'dateTo')
  +          };
  +
  +          if (filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo)
  +            throw Problem.user.invalidEntity({ reason: 'dateFrom must be before dateTo.' });
  +
  +          return vgAuth.listProjectSessions({ VgAppUserAuth }, filters, options);
  +        })
  +        .then((sessions) => {
  +          const total = sessions.length !== 0 && Number.isFinite(Number(sessions[0].total_count))
  +            ? Number(sessions[0].total_count)
  +            : sessions.length;
  +          response.set('X-Total-Count', total);
  +          return sessions.map((s) => ({
  +            id: s.id,
  +            appUserId: s.appUserId,
  +            createdAt: s.createdAt,
  +            expiresAt: s.expiresAt,
  +            ip: s.ip,
  +            userAgent: s.user_agent,
  +            deviceId: s.device_id,
  +            comments: s.comments
  +          }));
  +        })
  +  ));
  ```

- Date: 2025-12-22
  File: lib/resources/vg-app-user-auth.js
  Change summary: Add revoke single app-user session endpoint.
  Reason: Allow admins to deactivate individual app-user sessions.
  Risk/notes: Medium; new endpoint that terminates sessions.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/resources/vg-app-user-auth.js b/lib/resources/vg-app-user-auth.js
  index f8a0c24b..f6a0ff32 100644
  --- a/lib/resources/vg-app-user-auth.js
  +++ b/lib/resources/vg-app-user-auth.js
  @@ -150,6 +150,23 @@ module.exports = (service, endpoint, anonymousEndpoint) => {
           return sessions.map((s) => ({
             id: s.id,
             appUserId: s.appUserId,
             createdAt: s.createdAt,
             expiresAt: s.expires_at,
             ip: s.ip,
             userAgent: s.user_agent,
             deviceId: s.device_id,
             comments: s.comments
           }));
         })
     ));
  +
  +  // Revoke a single app-user session (admin/manager).
  +  service.post('/projects/:projectId/app-users/sessions/:sessionId/revoke', endpoint(
  +    ({ Projects, VgAppUserAuth, Sessions, Audits }, { auth, params }) =>
  +      Projects.getById(params.projectId)
  +        .then(getOrNotFound)
  +        .then((project) => auth.canOrReject('session.end', project))
  +        .then(() => VgAppUserAuth.getSessionById(parsePositiveInt(params.sessionId, 'sessionId')))
  +        .then(getOrNotFound)
  +        .then((session) => {
  +          if (session.projectId !== Number(params.projectId))
  +            return Problem.user.notFound();
  +          const revokedBy = auth.actor.orNull();
  +          return vgAuth.revokeSessionById({ Sessions, VgAppUserAuth, Audits }, session, revokedBy)
  +            .then(() => success);
  +        })
  +  ));
  ```

- Date: 2025-12-22
  File: lib/model/query/vg-app-user-auth.js
  Change summary: Store and query app-user session history from vg_app_user_sessions.
  Reason: Preserve login history even after sessions are reaped.
  Risk/notes: Medium; shifts history queries off sessions table.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/model/query/vg-app-user-auth.js b/lib/model/query/vg-app-user-auth.js
  index 52c9ce8b..bfe3dc9b 100644
  --- a/lib/model/query/vg-app-user-auth.js
  +++ b/lib/model/query/vg-app-user-auth.js
  @@ -83,8 +83,8 @@ const recordSession = ({ token, actorId, ip = null, userAgent = null, deviceId =
   -  run(sql`
   -    INSERT INTO vg_app_user_sessions (token, "actorId", ip, user_agent, device_id, comments)
   -    VALUES (${token}, ${actorId}, ${ip}, ${userAgent}, ${deviceId}, ${comments})
   +  run(sql`
   +    INSERT INTO vg_app_user_sessions (token, "actorId", ip, user_agent, device_id, comments, "createdAt", expires_at)
   +    VALUES (${token}, ${actorId}, ${ip}, ${userAgent}, ${deviceId}, ${comments}, ${createdAt}, ${expiresAt})
       ON CONFLICT (token) DO UPDATE
         SET "actorId" = EXCLUDED."actorId",
  @@ -92,7 +92,9 @@ const recordSession = ({ token, actorId, ip = null, userAgent = null, deviceId =
           ip = EXCLUDED.ip,
           user_agent = EXCLUDED.user_agent,
           device_id = EXCLUDED.device_id,
   -      comments = EXCLUDED.comments
   +      comments = EXCLUDED.comments,
   +      "createdAt" = EXCLUDED."createdAt",
   +      expires_at = EXCLUDED.expires_at
     `);
  
  -const getActiveSessionsByActorId = (actorId, options = QueryOptions.none) => ({ all }) =>
  +const getSessionsByActorId = (actorId, options = QueryOptions.none) => ({ all }) =>
     all(sql`
       SELECT
         count(*) OVER () AS total_count,
  -      s.token,
  -      s."createdAt",
  -      s."expiresAt",
  +      v.token,
  +      v."createdAt",
  +      v.expires_at,
         v.id,
  @@ -100,9 +102,8 @@ const getActiveSessionsByActorId = (actorId, options = QueryOptions.none) => ({ all }) =>
         v.user_agent,
         v.device_id,
         v.comments
  -    FROM sessions s
  -    JOIN vg_app_user_sessions v ON v.token = s.token
  -    WHERE s."actorId"=${actorId}
  -    ORDER BY s."createdAt" DESC
  +    FROM vg_app_user_sessions v
  +    WHERE v."actorId"=${actorId}
  +    ORDER BY v."createdAt" DESC
       ${page(options)}
     `);
  @@ -112,7 +113,7 @@ const projectSessionFilterer = (filters) => {
  -  if (filters.appUserId != null) conditions.push(sql`s."actorId"=${filters.appUserId});
  -  if (filters.dateFrom != null) conditions.push(sql`s."createdAt" >= ${filters.dateFrom});
  -  if (filters.dateTo != null) conditions.push(sql`s."createdAt" <= ${filters.dateTo});
  +  if (filters.appUserId != null) conditions.push(sql`v."actorId"=${filters.appUserId});
  +  if (filters.dateFrom != null) conditions.push(sql`v."createdAt" >= ${filters.dateFrom});
  +  if (filters.dateTo != null) conditions.push(sql`v."createdAt" <= ${filters.dateTo});
     return (conditions.length === 0) ? sql`true` : sql.join(conditions, sql` and `);
   };
  
  -const getActiveSessionsByProject = (filters = {}, options = QueryOptions.none) => ({ all }) =>
  +const getSessionsByProject = (filters = {}, options = QueryOptions.none) => ({ all }) =>
     all(sql`
       SELECT
         count(*) OVER () AS total_count,
  -      s."actorId" AS "appUserId",
  -      s."createdAt",
  -      s."expiresAt",
  +      v."actorId" AS "appUserId",
  +      v."createdAt",
  +      v.expires_at,
         v.id,
  @@ -121,9 +122,8 @@ const getActiveSessionsByProject = (filters = {}, options = QueryOptions.none) => ({ all }) =>
         v.user_agent,
         v.device_id,
         v.comments
  -    FROM sessions s
  -    JOIN vg_app_user_sessions v ON v.token = s.token
  -    JOIN field_keys fk ON fk."actorId" = s."actorId"
  +    FROM vg_app_user_sessions v
  +    JOIN field_keys fk ON fk."actorId" = v."actorId"
       WHERE ${projectSessionFilterer(filters)}
  -    ORDER BY s."createdAt" DESC
  +    ORDER BY v."createdAt" DESC
       ${page(options)}
     `);
  ```

- Date: 2025-12-22
  File: lib/domain/vg-app-user-auth.js
  Change summary: Persist session timestamps in vg_app_user_sessions.
  Reason: Keep login history after session reap.
  Risk/notes: Low.
  Related commits/PRs: vg-work history
  Diff:
  ```diff
  diff --git a/lib/domain/vg-app-user-auth.js b/lib/domain/vg-app-user-auth.js
  index 0f7d0a3c..d4fe06d7 100644
  --- a/lib/domain/vg-app-user-auth.js
  +++ b/lib/domain/vg-app-user-auth.js
  @@ -133,7 +133,9 @@ const login = async (container, payload) => {
     await VgAppUserAuth.recordSession({
       token: session.token,
       actorId: record.actorId,
       ip,
       userAgent,
       deviceId,
  -    comments
  +    comments,
  +    createdAt: session.createdAt,
  +    expiresAt: session.expiresAt
     });
  ```
