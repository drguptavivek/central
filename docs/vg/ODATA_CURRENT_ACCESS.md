# OData Access - Current Code Analysis

**Last Updated**: 2026-02-08
**Based on**: Permission checks in `lib/resources/odata.js` and role definitions in migrations

---

## TL;DR - Who Can Access OData Right Now?

```
✅ Web Admins (System Admins) - ALL have access
✅ Project Managers - ALL forms they manage have access
✅ Project Viewers - READ-ONLY to forms they view
❌ App Users (Field Keys) - NO access (permission denied)
❌ Public Links - NO access (no submission.read permission)
```

---

## Detailed Permission Analysis

### OData Permission Check

All OData endpoints check the same permission:

```javascript
// server/lib/resources/odata.js:85
.then((form) => auth.canOrReject('submission.read', form))
```

This means: **User MUST have `submission.read` permission on that form**.

---

## Current Roles & OData Access

### Role 1: Administrator (System Admin)

**Can access OData?** ✅ **YES - ALL forms**

**Reason**: Admins have `submission.read` verb in admin role

**Code source**: `lib/model/migrations/20181212-01-add-roles.js:51`
```javascript
const allVerbs = [
  'submission.read',  // ← Admins have this
  'submission.create',
  'submission.list',
  // ... other verbs
];
await db.insert(allVerbs.map((verb) => ({ roleId: adminRoleId, verb }))).into('grants');
```

**Assignment**: Admins are assigned admin role on `*` (all actees)
```javascript
// admin users get admin role on everything (*)
await db.insert(
  db.select(...).from('actors').where({ type: 'user' })
).into('assignments');
```

**OData Access**:
```bash
Admin with email: admin@example.com
  ├─ Can access: /projects/1/forms/form1.svc/Submissions ✅
  ├─ Can access: /projects/2/forms/form2.svc/Submissions ✅
  ├─ Can query: All submission fields
  └─ Can filter: All submissions (no restriction)
```

---

### Role 2: Project Manager (Project-scoped)

**Can access OData?** ✅ **YES - Only forms they manage**

**Reason**: Project Managers have `submission.read` verb

**Code source**: `lib/model/migrations/20190227-01-add-project-manager-role.js:13`
```javascript
const verbs = [
  'project.read', 'project.update', 'project.delete',
  'form.create', 'form.delete', 'form.list', 'form.read', 'form.update',
  'submission.create', 'submission.read',  // ← Managers have this
  'submission.list', 'submission.update',
  'field_key.create', 'field_key.delete', 'field_key.list',
  'assignment.list', 'assignment.create', 'assignment.delete'
];
```

**Assignment**: Via role assignment on specific project
```javascript
// Manager assigned to project actee (not * )
assignment {
  actorId: user.id,
  roleId: manager_role_id,
  acteeId: project.acteeId  // ← specific project, not *
}
```

**OData Access**:
```bash
Manager with email: manager@example.com
  ├─ Assigned to Project 1 as Manager
  │  ├─ Can access: /projects/1/forms/form1.svc/Submissions ✅
  │  ├─ Can access: /projects/1/forms/form2.svc/Submissions ✅
  │  └─ Can query: Submissions in Project 1
  │
  └─ NOT assigned to Project 2
     ├─ Cannot access: /projects/2/forms/form3.svc/Submissions ❌
     └─ Error: "Insufficient Rights"
```

---

### Role 3: Project Viewer (Project-scoped, Read-only)

**Can access OData?** ✅ **YES - READ-ONLY, only forms they view**

**Reason**: Project Viewers have `submission.read` verb

**Code source**: `lib/model/migrations/20190923-01-add-project-viewer-role.js:10-14`
```javascript
const verbs = [
  'project.read',
  'form.list', 'form.read',
  'submission.read',  // ← Viewers have this (read-only)
  'submission.list'
];
```

**Key Difference from Manager**: Viewers do NOT have:
- `submission.create` ❌
- `submission.update` ❌
- `form.create` ❌

**OData Access**:
```bash
Viewer with email: viewer@example.com
  ├─ Assigned to Project 1 as Viewer
  │  ├─ Can read: /projects/1/forms/form1.svc/Submissions ✅
  │  ├─ Can filter/sort: All queries work
  │  └─ CANNOT write: OData is read-only anyway
  │
  └─ NOT assigned to Project 2
     ├─ Cannot access: /projects/2/forms/form3.svc/Submissions ❌
     └─ Error: "Insufficient Rights"
```

---

### Role 4: App User (Field Key)

**Can access OData?** ❌ **NO - Permission Denied**

**Reason**: App Users do NOT have `submission.read` permission

**Code source**: `lib/model/migrations/20181212-01-add-roles.js:53-54`
```javascript
const appUserVerbs = [ 'form.list', 'form.read', 'submission.create' ];
// ↑ NO submission.read here!
await db.insert(appUserVerbs.map((verb) => ({ roleId: appUserRoleId, verb }))).into('grants');
```

**What they CAN do**:
- Create submissions (OpenRosa): `submission.create` ✅
- List forms: `form.list` ✅
- Read form schema: `form.read` ✅

**What they CANNOT do**:
- Query submission data: `submission.read` ❌
- Update submissions: `submission.update` ❌
- List submissions: `submission.list` ❌

**OData Access Result**:
```bash
App user with username: tableau_sync
  ├─ POST /projects/1/app-users/login → Gets bearer token ✅
  ├─ POST /projects/1/submission → Can upload forms via OpenRosa ✅
  │
  └─ GET /projects/1/forms/myform.svc/Submissions
     └─ Error: 401.2 Insufficient Rights ❌
        (no submission.read permission)
```

---

### Role 5: Public Link

**Can access OData?** ❌ **NO - No public_link role**

**Reason**: No role with `submission.read` assigned to public links

**What public links can do**:
- View empty form (for download)
- Submit forms (OpenRosa)
- Limited read access to form structure

**What they cannot do**:
- Query submissions via OData ❌
- Read any submission data ❌

---

## Permission Check Details

### How Permission Check Works

```javascript
// server/lib/model/query/auth.js:24-52
const can = (actor, verbs, actee) => ({ oneFirst }) => {
  // Queries assignments table:
  // SELECT EXISTS (
  //   SELECT 1 FROM assignments
  //   INNER JOIN roles WHERE role has the verb
  //   WHERE actorId = actor.id AND acteeId matches
  // )

  // Returns: true if actor has verb on actee, false otherwise
};
```

**Query Logic**:
1. Get the form's acteeId
2. Check if actor has a role assignment with that verb
3. Roles can be assigned at:
   - `*` = global (admins)
   - Project level (managers, viewers)
   - Form level (if configured)

---

## Real Scenario Testing

### Scenario 1: Admin Accessing OData

```
Admin: alice@example.com (admin role on *)

GET /projects/1/forms/myform.svc/Submissions

Step 1: Check permission
  auth.canOrReject('submission.read', form)

Step 2: Query database
  SELECT EXISTS (
    SELECT 1 FROM assignments
    WHERE actorId = alice.id
      AND acteeId matches form.acteeId or *
      AND role has submission.read
  )

Step 3: Result
  Assignments found:
    alice → admin role → * (global)
    Admin role has submission.read ✅

Response: ✅ Query succeeds
  Returns form metadata and all submissions
```

### Scenario 2: App User (Field Key) Trying OData

```
App User: tableau_sync (app_user role on project 1)

GET /projects/1/forms/myform.svc/Submissions
Authorization: Bearer FIELD_KEY_TOKEN

Step 1: Check permission
  auth.canOrReject('submission.read', form)

Step 2: Query database
  SELECT EXISTS (
    SELECT 1 FROM assignments
    WHERE actorId = field_key_actor.id
      AND acteeId matches form.acteeId
      AND role has submission.read
  )

Step 3: Result
  Assignments found:
    field_key → app_user role → project 1
    App_user role does NOT have submission.read ❌

Response: ❌ 401.2 Insufficient Rights
  Error: User does not have permission to access this resource
```

### Scenario 3: Project Manager Limited to Project

```
Manager: bob@example.com
  ├─ Manager role on Project 1
  └─ No role on Project 2

GET /projects/1/forms/form1.svc/Submissions ✅
  Permission check: YES (bob has manager role on project 1)
  Result: Returns submissions

GET /projects/2/forms/form2.svc/Submissions ❌
  Permission check: NO (bob has no role on project 2)
  Result: 401.2 Insufficient Rights
```

---

## Important: OData vs OpenRosa

| Operation | Endpoint | Method | Who Can? | Permission |
|-----------|----------|--------|----------|------------|
| **Query data** | `/forms/myform.svc/Submissions` | GET | Admins, Managers, Viewers | `submission.read` |
| **Create submission** | `/projects/:id/submission` (OpenRosa) | POST | Admins, Managers, App Users | `submission.create` |
| **Update submission** | `/forms/myform/submissions/:id` | PATCH | Admins, Managers | `submission.update` |

---

## Current Code Limitation

### Issue: App Users Cannot Query Data via OData

**Status**: ⚠️ **CURRENT LIMITATION**

App users (field keys) cannot access OData even though they:
- ✅ Are used by Tableau in some deployments
- ✅ Have valid bearer tokens
- ✅ Are authenticated

**Reason**: Missing `submission.read` permission in app_user role

**Code that prevents this**:
```javascript
// 20181212-01-add-roles.js:53
const appUserVerbs = [ 'form.list', 'form.read', 'submission.create' ];
// Missing: 'submission.read'
```

**If this were to be changed** (not current):
```javascript
const appUserVerbs = [
  'form.list',
  'form.read',
  'submission.create',
  'submission.read'  // ← Would need to be added
];
```

---

## Security Implication

### Why App Users Don't Have `submission.read`

**Design Rationale**:
- App users (field workers) are meant to **create** submissions (via Collect)
- App users are NOT meant to **query** data (via OData)
- Reading data would expose sensitive information to field workers
- Data queries should come from admins or managers (trusted users)

**Current Access Model**:
```
Field Worker (App User)
  ├─ Can create submissions (Collect app)
  │  ├─ Via OpenRosa: POST /submission
  │  ├─ Permission: submission.create ✅
  │  └─ Via: app-users/login endpoint
  │
  └─ Cannot query data (OData)
     ├─ Via OData: GET /forms/.svc/Submissions
     ├─ Permission: NO submission.read ❌
     └─ Purpose: Prevent unauthorized data access
```

---

## Summary Table: Current OData Access by User Type

| User Type | Role | OData Access | Forms Accessible | Reason |
|-----------|------|--------------|------------------|--------|
| **Admin** | Administrator | ✅ YES | ALL | Has `submission.read` on `*` |
| **Manager** | Project Manager | ✅ YES | Their projects | Has `submission.read` on project |
| **Viewer** | Project Viewer | ✅ YES (read-only) | Their projects | Has `submission.read` on project |
| **Field Worker** | App User | ❌ NO | None | NO `submission.read` permission |
| **Public Link** | None | ❌ NO | None | No role with `submission.read` |

---

## Code References

**Permission Checks**:
- `lib/resources/odata.js:85` - OData call site
- `lib/resources/odata.js:91` - Draft form call site
- `lib/model/query/auth.js:24-52` - Permission logic

**Role Definitions**:
- Admin role: `lib/model/migrations/20181212-01-add-roles.js:51`
- App User role: `lib/model/migrations/20181212-01-add-roles.js:54`
- Project Manager: `lib/model/migrations/20190227-01-add-project-manager-role.js`
- Project Viewer: `lib/model/migrations/20190923-01-add-project-viewer-role.js`

**Assignments**:
- Admin assignments: `lib/model/migrations/20181212-01-add-roles.js:71-75`
- App user assignments: `lib/model/migrations/20181212-01-add-roles.js:83-86`
