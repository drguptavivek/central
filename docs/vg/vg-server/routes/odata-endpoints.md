# OData Endpoints

> **Last Updated:** 2026-01-14
> **Protocol:** OData v4
> **Purpose:** Data query protocol for submissions and entities

---

## Overview

OData (Open Data Protocol) endpoints provide RESTful access to form submissions and entities with:
- SQL-like query syntax (`$filter`, `$select`, `$orderby`)
- Metadata endpoints
- Entity access by UUID

**WAF Priority:** HIGH - These endpoints are called frequently for data sync.

---

## Protocol Syntax

### OData Query Operators

| Operator | Example | SQL Equivalent | WAF Impact |
|----------|---------|----------------|------------|
| `$filter` | `?$filter=field eq 'value'` | `WHERE field = 'value'` | **HIGH** - Triggers SQLi rules |
| `$select` | `?$select=field1,field2` | `SELECT field1,field2` | Low |
| `$orderby` | `?$orderby=field desc` | `ORDER BY field DESC` | Low |
| `$top` | `?$top=100` | `LIMIT 100` | Low |
| `$skip` | `?$skip=100` | `OFFSET 100` | Low |

**WAF Issue:** `$filter` syntax contains SQL keywords (`and`, `or`, `eq`, `ne`) that trigger CRS SQL injection rules.

---

## Current CRS Exclusions

**Already Configured:**
```nginx
# Location: crs_custom/20-odk-odata-exclusions.conf
SecRule REQUEST_URI "@endsWith .svc" \
    "id:1000,phase:2,pass,nolog,ctl:ruleRemoveById=942290"
```

**Rule 942290** - SQL injection detection is disabled for all `.svc` endpoints.

**Reason:** OData filter syntax (`$filter=status eq 'active'`) looks like SQL injection to CRS rules.

---

## Endpoints

### 1. Submission Feed Metadata

**Route:** `GET /v1/projects/:projectId/forms/:xmlFormId.svc`

**File:** `server/lib/resources/odata.js:26-28`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | **HIGH** (data sync) |
| **Payload** | MEDIUM (XML response) |
| **Risk** | NONE |
| **CRS Exclusions** | **942290** |
| **Special** | Returns service document |

**Request:**
```
GET /v1/projects/1/forms/basic.svc
```

**Response:**
```xml
<service xmlns="http://www.w3.org/2007/app">
  <workspace>
    <title>basic</title>
    <collection href="Submissions">
      <title>Submissions</title>
    </collection>
  </workspace>
</service>
```

**WAF Considerations:**
- Returns list of available entity sets
- No query parameters

---

### 2. Submission Metadata

**Route:** `GET /v1/projects/:projectId/forms/:xmlFormId.svc/($metadata)`

**File:** `server/lib/resources/odata.js:35-47`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | MEDIUM (initial connection) |
| **Payload** | SMALL (<10KB) |
| **Risk** | NONE |
| **CRS Exclusions** | **942290** |

**Request:**
```
GET /v1/projects/1/forms/basic.svc/($metadata)
```

**Response:**
```xml
<edmx:Edmx>
  <edmx:DataServices>
    <Schema xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityType Name="Submissions">
        <Property Name="__id" Type="Edm.String"/>
        <Property Name="status" Type="Edm.String"/>
        <!-- ... more fields ... -->
      </EntityType>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>
```

**WAF Considerations:**
- Describes entity structure
- Called by clients to understand data model

---

### 3. Submission Feed (All Records)

**Route:** `GET /v1/projects/:projectId/forms/:xmlFormId.svc/Submissions`

**File:** `server/lib/resources/odata.js:61-67`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | **HIGH** (data sync) |
| **Payload** | **LARGE** (all data) |
| **Risk** | NONE |
| **CRS Exclusions** | **942290** |
| **Special** | Supports `$filter`, `$top`, `$skip` |

**Request:**
```
GET /v1/projects/1/forms/basic.svc/Submissions?$top=100
```

**Response:**
```xml
<feed>
  <entry>
    <content>
      <m:properties>
        <d:__id>uuid-123</d:__id>
        <d:status>submitted</d:status>
      </m:properties>
    </content>
  </entry>
  <!-- ... more entries ... -->
</feed>
```

**WAF Considerations:**
- **HIGH LOAD**: Primary data sync endpoint
- **LARGE RESPONSE**: Can return thousands of records
- **Query parameters**: Can be complex ($filter with multiple conditions)
- **CRS 942290 EXCLUDED**: Required for $filter syntax

---

### 4. Single Submission by UUID

**Route:** `GET /v1/projects/:projectId/forms/:xmlFormId.svc/Submissions(:uuid)`

**File:** `server/lib/resources/odata.js:57-59`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | MEDIUM |
| **Payload** | MEDIUM (single record) |
| **Risk** | NONE |
| **CRS Exclusions** | **942290** |

**Request:**
```
GET /v1/projects/1/forms/basic.svc/Submissions(uuid='12345678-1234-1234-1234-123456789abc')
```

**WAF Considerations:**
- UUID in URL path
- Single record response

---

### 5. Entity Feed Metadata

**Route:** `GET /v1/projects/:projectId/datasets/:name.svc`

**File:** `server/lib/resources/odata-entities.js:26-28`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | MEDIUM |
| **Payload** | SMALL |
| **Risk** | NONE |
| **CRS Exclusions** | **942290** |

**WAF Considerations:**
- Similar structure to submission endpoints
- For entity datasets (managed entities)

---

### 6. Entity Metadata

**Route:** `GET /v1/projects/:projectId/datasets/:name.svc/($metadata)`

**File:** `server/lib/resources/odata-entities.js:34-41`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | MEDIUM |
| **Payload** | SMALL |
| **Risk** | NONE |
| **CRS Exclusions** | **942290** |

---

### 7. Entity Feed

**Route:** `GET /v1/projects/:projectId/datasets/:name.svc/Entities`

**File:** `server/lib/resources/odata-entities.js:43-54`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | MEDIUM |
| **Payload** | **LARGE** (all entities) |
| **Risk** | NONE |
| **CRS Exclusions** | **942290** |

**WAF Considerations:**
- Returns all entities in dataset
- Can be very large response

---

### 8. Draft Submission Endpoints

**Route:** `GET /v1/projects/:projectId/forms/:xmlFormId/draft.svc/*`

**File:** `server/lib/resources/odata.js:87-95`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | MEDIUM (testing) |
| **Payload** | MEDIUM |
| **Risk** | NONE |
| **CRS Exclusions** | **942290** |

**WAF Considerations:**
- Same as production endpoints but for draft forms
- Used for testing before publishing

---

## OData Query Examples

### Filter Examples

| Query | Purpose | SQL-Like Pattern |
|-------|---------|-------------------|
| `?$filter=status eq 'submitted'` | Equality | `WHERE status = 'submitted'` |
| `?$filter=createdAt gt 2023-01-01` | Greater than | `WHERE createdAt > '2023-01-01'` |
| `?$filter=age ge 18` | Greater or equal | `WHERE age >= 18` |
| `?$filter=name ne 'test'` | Not equal | `WHERE name != 'test'` |
| `?$filter=status eq 'submitted' and age ge 18` | And | `WHERE status = 'submitted' AND age >= 18` |
| `?$filter=status eq 'submitted' or status eq 'pending'` | Or | `WHERE status = 'submitted' OR status = 'pending'` |

**WAF Impact:** All `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `and`, `or` keywords trigger SQLi rules.

### Select Example

```
GET /v1/projects/1/forms/basic.svc/Submissions?$select=__id,status,createdAt
```

**Purpose:** Limit returned fields (column selection)

### Order By Example

```
GET /v1/projects/1/forms/basic.svc/Submissions?$orderby=createdAt desc
```

**Purpose:** Sort results

### Paging Example

```
GET /v1/projects/1/forms/basic.svc/Submissions?$top=100&$skip=200
```

**Purpose:** Pagination (skip 200, take next 100)

---

## WAF Configuration Summary

### Current Exclusions

**File:** `crs_custom/20-odk-odata-exclusions.conf`
```nginx
SecRule REQUEST_URI "@endsWith .svc" \
    "id:1000,phase:2,pass,nolog,ctl:ruleRemoveById=942290"
```

**What this does:**
- Disables rule 942290 (SQLi detection) for all `.svc` endpoints
- Applied in phase 2 (after request body parsing)
- Passes through (doesn't block) without logging

**Why this is necessary:**
- OData `$filter` parameter contains SQL-like syntax
- Examples that trigger 942290:
  - `?$filter=field eq 'value'`
  - `?$filter=status eq 'active' or age gt 18`
  - `?$filter=name ne 'test' and status eq 'pending'`

### Recommended Additional Exclusions

**Consider adding for query length:**
```nginx
# OData queries can be very long (complex filters)
SecRule REQUEST_URI "@rx \.svc\?.{1000,}" \
    "id:2001,phase:1,pass,nolog,ctl:ruleEngine=On"
```

**Consider for response size:**
```nginx
# OData responses can be very large
SecRule REQUEST_URI "@rx \.svc/Submissions$" \
    "id:2002,phase:3,pass,nolog,ctl:responseBodyLimit=104857600"
```

---

## Client Webapp Usage

### Where OData is Used in the Client

**1. OData "Analyze" Modal** (`client/src/components/odata/analyze.vue`)

Purpose: Connect external tools to OData data feeds

**Supported Tools:**
- **Microsoft Power BI** - Business intelligence dashboards
- **Microsoft Excel** - Data analysis via Power Query
- **Python (pyODK)** - Official Python client for automation
- **R (ruODK)** - Community R package for data science
- **Other/API** - Generic OData clients

**UI Behavior:**
- Modal displays OData URL for copy-paste
- Shows tool-specific help documentation
- **DISABLED when OIDC is enabled** (`v-if="!config.oidcEnabled"`)
- Accessible from submission view "Connect Data" button

**2. Submission Table View** (`client/src/components/submission/table-view.vue`)

Purpose: Internal OData client for fetching submission data

**Usage:**
- Calls `apiPaths.odataSubmissions()` for data
- Uses `$filter`, `$top`, `$skip`, `$select`, `$orderby` parameters
- Implements pagination with `$skiptoken` for server-driven paging
- Filters by `__system/submissionDate` and `__system/deletedAt`

**Request Example:**
```
GET /v1/projects/1/forms/basic.svc/Submissions?
  $top=250&
  $skip=0&
  $filter=__system/submissionDate le '2026-01-14T12:00:00Z' and (__system/deletedAt eq null or __system/deletedAt gt '2026-01-14T12:00:00Z')&
  $select=__id,__system,name,age&
  $orderby=__system/submissionDate desc&
  $wkt=true&
  $count=true
```

**3. Entity Data View** (`client/src/components/dataset/entities.vue`)

Purpose: View and manage entity datasets

**Usage:**
- Calls `apiPaths.odataEntitiesSvc()` for entity data
- Similar pagination and filtering as submissions

---

## Security Analysis

### SQL Injection Risk: **NONE** ✅

**Why OData is Safe from SQL Injection:**

The OData implementation uses **Slonik ORM** with parameterized queries. The filter syntax is parsed into an AST by `odata-v4-parser`, then transformed into Slonik SQL fragments.

**Code Evidence:**

**1. OData Filter Transformation** (`server/lib/data/odata-filter.js:10-110`)

```javascript
const { sql } = require('slonik');
const odataParser = require('odata-v4-parser');

const odataFilter = (expr, odataToColumnMap) => {
  // Parses OData expression into AST
  const op = (node) => {
    if (node.type === 'FirstMemberExpression') {
      // Only allow whitelisted fields
      if (odataToColumnMap.has(node.raw)) {
        return sql.identifier(odataToColumnMap.get(node.raw).split('.'));
      } else {
        throw Problem.internal.unsupportedODataField({ text: node.raw });
      }
    } else if (node.type === 'Literal') {
      // Safely extract literal value
      return (node.raw === 'null') ? null
        : (/^'.*'$/.test(node.raw)) ? node.raw.slice(1, node.raw.length - 1)
          : node.raw;
    } else if (node.type === 'EqualsExpression') {
      // Use Slonik's parameterized comparison
      return booleanOp(sql`${left} IS NOT DISTINCT FROM ${right}`);
    } else if (node.type === 'LesserThanExpression') {
      return booleanOp(sql`${op(node.value.left)} < ${op(node.value.right)}`);
    }
    // ... more operators
  };
  return op(parseOdataExpr(expr));
};
```

**2. Field Whitelisting** (`server/lib/data/odata-filter.js:66-71`)

```javascript
if (node.type === 'FirstMemberExpression' || node.type === 'RootExpression') {
  if (odataToColumnMap.has(node.raw)) {
    // ONLY whitelisted fields allowed
    return sql.identifier(odataToColumnMap.get(node.raw).split('.'));
  } else {
    // Reject unknown fields
    throw Problem.internal.unsupportedODataField({ text: node.raw });
  }
}
```

**3. Authorization Enforcement** (`server/lib/resources/odata.js:80-85`)

```javascript
odataResource('/projects/:projectId/forms/:xmlFormId.svc', false, (Forms, auth, params) =>
  Forms.getByProjectAndXmlFormId(params.projectId, params.xmlFormId, Form.PublishedVersion)
    .then(getOrNotFound)
    .then(ensureDef)
    .then((form) => auth.canOrReject('submission.read', form))); // ← PERMISSION CHECK
```

**4. Entity Authorization** (`server/lib/resources/odata-entities.js:43-46`)

```javascript
service.get('/projects/:projectId/datasets/:name.svc/Entities', endpoint.odata.json(async ({ Datasets, Projects }, { auth, params }) => {
  const project = await Projects.getById(params.projectId).then(getOrNotFound);
  await auth.canOrReject('entity.list', project); // ← PERMISSION CHECK
  // ...
}));
```

**What This Means:**
- ✅ All SQL queries are parameterized via Slonik's `sql` template literal
- ✅ Only fields in `odataToColumnMap` can be queried (whitelist validation)
- ✅ Users must have `submission.read` or `entity.list` permission
- ✅ CRS 942290 exclusion is SAFE because no SQL injection is possible

---

### DoS via Complex Queries: **LOW-MEDIUM** ⚠️

**Attack Vector:**
- Nested `$filter` expressions: `?$filter=((a eq 1 and b eq 2) or (c eq 3 and d eq 4))`
- Deep `$expand` operations (not heavily used in current implementation)
- No query complexity limit found in code

**Current Protections:**
- `$top` parameter limits results (default: Infinity, should be capped)
- `$skip` parameter for offset
- `$skiptoken` for server-driven pagination

**Recommendation:**
Add query complexity limits to prevent parser DoS:
```javascript
// server/lib/util/odata.js
const MAX_FILTER_DEPTH = 10;
const MAX_FILTER_NODES = 50;
```

---

### Data Scraping: **MEDIUM** ⚠️

**Attack Vector:**
- Authenticated users can export all data with `$filter=__system/deletedAt eq null`
- No rate limiting per project
- OData URLs can be shared externally once authenticated

**Current Protections:**
- Authentication required (Field Key or Bearer token)
- Authorization enforced per form/dataset
- Disabled when OIDC is enabled (client-side check)

**Recommendation:**
- Add per-project rate limiting
- Consider audit logging for OData access
- Monitor for bulk export patterns

---

## Can OData be Disabled as an Attack Vector?

### Current State

**Client-Side:**
- OData modal is **ALREADY DISABLED** when OIDC is enabled
- Code: `v-if="!config.oidcEnabled"` in `client/src/components/odata/analyze.vue`

**Server-Side:**
- OData endpoints are **ALWAYS ACTIVE** regardless of OIDC setting
- No server-side disable mechanism exists

### Options to Disable OData

#### Option 1: Client-Side Only (Current Status)

**Impact:**
- Web UI won't show OData connection modal
- External tools can still access OData if they have URL + credentials
- No code changes needed (already implemented)

**Security:**
- ⚠️ **NOT SUFFICIENT** - endpoints still accessible via direct API calls

#### Option 2: Server-Side Middleware (Recommended)

**Implementation:**

```javascript
// server/lib/http/endpoint.js
// Add to odata endpoint definition:

const odataResource = (base, draft, getForm) => {
  // Check if OIDC is enabled
  service.get(base, endpoint.odata.json(({ Forms, env }, { auth, params, originalUrl }) => {
    if (env.oidcEnabled) {
      throw Problem.user.notFound(); // or Problem.user.featureDisabled()
    }
    return getForm(Forms, auth, params)
      // ... rest of endpoint
  }));
};
```

**Impact:**
- OData endpoints return 404 when OIDC is enabled
- External tools cannot access OData
- Requires server code change

**Security:**
- ✅ **EFFECTIVE** - endpoints completely disabled

#### Option 3: Project-Level Flag (Flexible)

**Implementation:**

```sql
-- Add to projects table:
ALTER TABLE projects ADD COLUMN odata_enabled BOOLEAN NOT NULL DEFAULT true;
```

```javascript
// server/lib/resources/odata.js
service.get(base, endpoint.odata.json(async ({ Forms, Projects }, { auth, params }) => {
  const project = await Projects.getById(params.projectId);
  if (!project.odataEnabled) {
    throw Problem.user.featureDisabled();
  }
  // ... rest of endpoint
}));
```

**Impact:**
- Per-project OData enable/disable
- Allows selective OData access
- Requires database migration + UI changes

**Security:**
- ✅ **MOST FLEXIBLE** - granular control per project

---

## Access Restriction Options

### Current Access Controls

| Control | Implementation | Effectiveness |
|---------|----------------|---------------|
| **Authentication** | Field Key / Bearer token | ✅ High |
| **Authorization** | `submission.read` / `entity.list` | ✅ High |
| **Field Whitelisting** | `odataToColumnMap` validation | ✅ High |
| **Parameterized Queries** | Slonik ORM | ✅ High |
| **OIDC Disable** | Client-side only | ⚠️ Low |

### Recommended Additional Restrictions

### 1. Rate Limiting (HIGH PRIORITY) 🔴

**Current Status:**
- ❌ **NO rate limiting on OData endpoints** (security gap)
- ✅ Login endpoints have rate limiting (20/15min → 30min lock)
- ❌ No WAF-level rate limiting in nginx config

**Why Rate Limiting is Needed:**

| Threat | Risk Level | Attack Vector |
|--------|------------|---------------|
| **Data Scraping** | **HIGH** | Authenticated user exports all data with `$top=10000` + pagination |
| **DoS via Complex Queries** | **MEDIUM** | Nested `$filter` expressions exhaust database CPU |
| **Automated Tool Abuse** | **MEDIUM** | Power BI/Excel auto-refresh every minute |

**Attack Example - Data Scraping:**
```bash
# Authenticated user can export ALL data without rate limiting:
curl "https://central.example.com/v1/projects/1/forms/basic.svc/Submissions?$filter=__system/deletedAt%20eq%20null&$top=10000"

# Repeated with pagination (no limit on requests):
curl "https://central.example.com/v1/projects/1/forms/basic.svc/Submissions?$filter=__system/deletedAt%20eq%20null&$top=10000&$skip=10000"
curl "https://central.example.com/v1/projects/1/forms/basic.svc/Submissions?$filter=__system/deletedAt%20eq%20null&$top=10000&$skip=20000"
# ... continues indefinitely
```

**Impact:**
- Unauthorized bulk data export
- Privacy violations (GDPR, HIPAA)
- Competitive intelligence theft
- Bandwidth exhaustion
- Database performance degradation

---

### Rate Limiting Options: Separation of Concerns

**Important:** Avoid multiple rate limiting layers for the same purpose - this causes configuration conflicts and difficult debugging.

**Recommended Approach - Choose ONE primary method per concern:**

| Concern | Layer | What It Handles | Why |
|----------|-------|-----------------|-----|
| **Brute Force Protection** | **Nginx** | IP-based request limits | Fastest, blocks at edge, protects all layers |
| **Business Logic Limits** | **Application** | User/project quotas | Per-user limits, project overrides, configurable |
| **Security Rules** | **ModSecurity** | SQLi, XSS, attack patterns | CRS integration, NOT rate limiting |

**What NOT to do:**
- ❌ Don't use ModSecurity for rate limiting (Nginx is simpler and faster)
- ❌ Don't use both Nginx AND ModSecurity for same rate limits (conflicts)
- ❌ Don't rely solely on app-level for brute force protection (too slow)

**Recommended Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│                        LAYER SEPARATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   NGINX      │    │  ModSecurity │    │   Application    │   │
│  │   Edge       │    │  WAF         │    │   Server         │   │
│  └──────┬──────┘    └──────┬───────┘    └────────┬─────────┘   │
│         │                  │                     │              │
│         │                  │                     │              │
│  ┌──────▼──────────────────▼─────────────────────▼──────────┐  │
│  │              RATE LIMITING RESPONSIBILITY                 │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  Nginx: IP-based brute force protection (20 req/min)    │  │
│  │  ModSecurity: SQLi, XSS, attack patterns (NO rate limit)│  │
│  │  Application: User/project quotas (100 req/min/user)    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation Options (Choose ONE or TWO complementary):**

| Option | Layers | When to Use | Complexity |
|--------|--------|-------------|------------|
| **Nginx Only** | Nginx | Simple deployment, IP-based limits only | Low |
| **Nginx + Application** | Nginx + App | Production, need user-based limits | Medium |
| **ModSecurity + Application** | WAF + App | Already using WAF, need detailed logging | Medium |

**Recommendation for Most Deployments:**

```
Nginx (IP brute force) + Application (User/project quotas)
```

- **Nginx** handles IP-based limits (fast, protects against DoS)
- **Application** handles user-based limits (business logic, configurable)
- **ModSecurity** handles security rules (SQLi, XSS) but NOT rate limiting

This separation ensures:
✅ Clear responsibility for each layer
✅ No configuration conflicts
✅ Easier debugging
✅ Best performance

---

### Option A: Nginx Native Rate Limiting (Recommended for Simplicity)

**File:** `files/nginx/odk.conf.template`

**Pros:** Simpler configuration, battle-tested, fastest performance

```nginx
# ============================================================================
# Nginx Native Rate Limiting for OData Endpoints
# Add to http block in odk.conf.template
# ============================================================================

# Define rate limit zones in http block (outside server block)
http {
    # Zone for OData endpoints (per IP) - 100 req/min
    limit_req_zone $binary_remote_addr zone=odata_zone:10m rate=100r/m;

    # Zone for submission endpoints (per IP) - 50 req/min
    limit_req_zone $binary_remote_addr zone=submission_zone:10m rate=50r/m;

    # Zone for form list (per IP) - 20 req/min
    limit_req_zone $binary_remote_addr zone=formlist_zone:10m rate=20r/m;

    # Zone for general project access (per IP) - 200 req/min
    limit_req_zone $binary_remote_addr zone=project_zone:10m rate=200r/m;

    # Zone for complex queries (long query strings) - 10 req/min
    limit_req_zone $binary_remote_addr zone=complex_zone:10m rate=10r/m;
}

# ============================================================================
# Apply rate limiting to OData endpoints
# Add inside server block
# ============================================================================

server {
    # Apply rate limiting to OData endpoints
    location ~ ^/v1/.*\.svc {
        # Stricter limit for Submissions feed (highest traffic)
        location ~ Submissions$ {
            limit_req zone=submission_zone burst=10 nodelay;
            limit_req_status 429;
        }

        # Standard OData limit (burst up to 20, no delay)
        limit_req zone=odata_zone burst=20 nodelay;
        limit_req_status 429;

        # Stricter limit for complex queries (>500 char query string)
        if ($args ~ ".{500,}") {
            limit_req zone=complex_zone burst=5 nodelay;
        }

        # Pass to backend (existing config)
        # ...
    }

    # Apply rate limiting to submission endpoints
    location ~ ^/v1/.*\/submission$ {
        limit_req zone=submission_zone burst=10 nodelay;
        limit_req_status 429;
        # Pass to backend (existing config)
        # ...
    }

    # Apply rate limiting to form list (OpenROSA sync)
    location ~ ^/v1/\d+/formList$ {
        limit_req zone=formlist_zone burst=5 nodelay;
        limit_req_status 429;
        # Pass to backend (existing config)
        # ...
    }

    # Per-project rate limiting (prevents scraping specific projects)
    location ~ ^/v1/projects/\d+/ {
        limit_req zone=project_zone burst=30 nodelay;
        limit_req_status 429;
        # Pass to backend (existing config)
        # ...
    }
}
```

**Nginx Rate Limiting Parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `zone` | Zone name and shared memory size | `zone=odata_zone:10m` (10MB) |
| `rate` | Requests per second/minute | `rate=100r/m` = 100 per minute |
| `burst` | Burst size for temporary spikes | `burst=20` (allow 20 excess requests) |
| `nodelay` | Don't delay burst requests (reject immediately) | `nodelay` |
| `limit_req_status` | HTTP status code when limit exceeded | `429` (Too Many Requests) |

**How Burst Works:**
```
Without burst:  ████░░░░░ (strict, rejects after limit)
With burst+nodelay: ███████████████░░ (allows burst, then rejects)
With burst+delay: ███████████████──── (delays excess requests)
```

---

### Option B: ModSecurity WAF Rate Limiting (NOT Recommended)

**⚠️ NOT RECOMMENDED** - Use Nginx native rate limiting instead (simpler, faster, less conflicts)

**Only use ModSecurity for rate limiting if:**
- You already have ModSecurity rules and want detailed audit logging
- You need per-project tracking at the edge layer
- You're already comfortable with ModSecurity syntax

**File:** `crs_custom/30-odk-odata-rate-limiting.conf`

```nginx
# ============================================================================
# OData Endpoint Rate Limiting
# Prevents data scraping, DoS, and automated tool abuse
# ============================================================================

# Per-IP rate limit for OData endpoints (100 requests/minute)
SecRule REQUEST_URI "@rx \.svc" \
    "id:3010,phase:1,deny,status:429, \
    setvar:ip.odata_counter=+1,expirevar:ip.odata_counter=60, \
    t:count,deny,msg='OData rate limit exceeded (100/60s)'"

# Per-IP rate limit for OData Submissions feed (highest traffic)
# Stricter limit for the most expensive endpoint
SecRule REQUEST_URI "@rx \.svc/Submissions$" \
    "id:3011,phase:1,deny,status:429, \
    setvar:ip.odata_submissions_counter=+1,expirevar:ip.odata_submissions_counter=60, \
    t:count,deny,msg='OData Submissions rate limit exceeded (50/60s)', \
    setvar:ip.odata_submissions_counter=0,expirevar:ip.odata_submissions_counter=60, \
    t:count,deny"

# Per-project rate limit (prevent scraping of specific projects)
# Limits requests per project ID to prevent targeted scraping
SecRule REQUEST_URI "@rx ^/v1/projects/(\d+)/.*\.svc" \
    "id:3012,phase:1,deny,status:429, \
    setvar:ip.project_%{MATCHED_VAR}_counter=+1,expirevar:ip.project_%{MATCHED_VAR}_counter=60, \
    t:count,deny,msg='Project OData rate limit exceeded (200/60s)'"

# Stricter limit for complex queries (large $filter expressions)
# Limits queries with long filter strings (potential DoS)
SecRule REQUEST_URI "@rx \.svc\?.{500,}" \
    "id:3013,phase:1,deny,status=429, \
    setvar:ip.odata_complex_counter=+1,expirevar:ip.odata_complex_counter=60, \
    t:count,deny,msg='Complex OData query rate limit exceeded (10/60s)'"
```

**Recommended Limits by Endpoint:**

| Endpoint Pattern | Limit | Duration | Scope | Priority |
|------------------|-------|----------|-------|----------|
| `/v1/.../formList` | 20 | 1min | IP | HIGH (OpenROSA sync) |
| `/v1/.../.svc/Submissions` | 50 | 1min | IP | HIGH (data feed) |
| `/v1/.../.svc/Entities` | 100 | 1min | IP | MEDIUM (entities) |
| `/v1/.../.svc/*` (general) | 100 | 1min | IP | MEDIUM (all OData) |
| `/v1/.../.svc/*` (complex) | 10 | 1min | IP | HIGH (DoS protection) |
| `/v1/projects/:id/*` (general) | 200 | 1min | IP | MEDIUM (per-project) |

---

### Option C: Application-Level Rate Limiting (Complementary to Nginx)

**Recommended:** Use with Nginx for complete protection
- **Nginx** - IP-based brute force protection (edge layer)
- **Application** - User/project-based quotas (business logic)

**For a production-ready, modular rate limiting system following the VG auth pattern:**

**See:** `docs/vg/vg-server/routes/vg-rate-limiting-design.md` for complete design specification.

**Quick Summary of Modular Design:**

Following the VG fork pattern used for web-user and app-user authentication:

```
server/lib/
├── domain/vg-rate-limit.js         # Business logic, orchestration
├── model/query/vg-rate-limit.js    # Database queries (audits table)
├── middleware/vg-rate-limit.js     # Express middleware
└── resources/                       # Existing endpoints use middleware
```

**Key Features:**
- ✅ User-based rate limiting (not just IP)
- ✅ Project-level settings overrides via `vg_settings` table
- ✅ Configurable limits (per endpoint type)
- ✅ Uses existing `audits` table (no new tables needed)
- ✅ Follows established VG patterns

**Example Usage:**

```javascript
// server/lib/resources/odata.js
const { odataRateLimit } = require('../middleware/vg-rate-limit');

module.exports = (service, endpoint) => {
  service.get(`${base}/:table`,
    odataRateLimit(),  // ← Apply rate limiting
    endpoint.odata.json(async ({ Forms, Submissions }, { auth, params }) => {
      // ... existing endpoint code
    })
  );
};
```

**Settings in Database:**

```sql
-- Global default
INSERT INTO vg_settings (key, value) VALUES
  ('vg_rate_limit_odata_per_minute', '100'),
  ('vg_rate_limit_enabled', 'true');

-- Project override (stricter)
INSERT INTO vg_project_settings (project_id, key, value) VALUES
  (123, 'vg_rate_limit_odata_per_minute', '10');

-- Project disable (trusted project)
INSERT INTO vg_project_settings (project_id, key, value) VALUES
  (456, 'vg_rate_limit_enabled', 'false');
```

**Pros/Cons:**

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **Nginx Only** | Simple, fast, battle-tested | IP-based only, no user context | Simple deployment |
| **Nginx + Application** | Best of both: edge protection + business logic | More implementation effort | Production (recommended) |
| **ModSecurity + Application** | Detailed logging + business logic | More complex syntax | Already heavily using WAF |

**Final Recommendation:**

```
┌────────────────────────────────────────────────────────────┐
│  PRODUCTION RECOMMENDATION                                 │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Deploy Nginx native rate limiting (immediate)          │
│     - Fast, simple, protects all layers                    │
│     - IP-based limits for brute force protection           │
│                                                             │
│  2. Implement modular application-level rate limiting      │
│     - User-based quotas (per user, not per IP)            │
│     - Project-level overrides via vg_settings              │
│     - Follows VG auth pattern (domain/model/middleware)    │
│                                                             │
│  3. ModSecurity for security rules only                   │
│     - SQLi, XSS, attack detection                          │
│     - NOT for rate limiting (use Nginx instead)            │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

### Current Rate Limiting in ODK Central

**What EXISTS:**
| Endpoint Type | Rate Limiting | Implementation |
|---------------|---------------|----------------|
| Web User Login (`POST /v1/sessions`) | ✅ Yes | IP: 20/15min → 30min lock; User: 5/5min → 10min lock |
| App User Login (`POST /v1/projects/:id/app-users/login`) | ✅ Yes | IP: 20/15min → 30min lock |
| OData queries | ❌ **NO** | None |
| Submission downloads | ❌ **NO** | None |
| All other GET endpoints | ❌ **NO** | None |

**Code References:**
- `server/lib/model/query/vg-web-user-auth.js` - Web user login rate limiting
- `server/lib/model/query/vg-app-user-ip-rate-limit.js` - App user login rate limiting
- `server/lib/resources/sessions.js` - Login lockout enforcement

---

### 2. IP-Based Restrictions

**WAF Config:**
```nginx
# Only allow specific IPs to access OData
SecRule REQUEST_URI "@rx \.svc" \
    "id:3001,phase:1,deny,status:403, \
    t:ipMatch,ipMatchFromFile:/etc/modsecurity/odata-allowlist.txt"
```

**Use Case:**
- Restrict OData to known office IPs
- Block external access while keeping API available

### 3. Query Complexity Limits

**Server-Side:**
```javascript
// server/lib/data/odata-filter.js
const countNodes = (node) => {
  if (!node || !node.type) return 0;
  let count = 1;
  if (node.value) {
    if (node.value.left) count += countNodes(node.value.left);
    if (node.value.right) count += countNodes(node.value.right);
    if (node.value.parameters) {
      count += node.value.parameters.reduce((sum, p) => sum + countNodes(p), 0);
    }
  }
  return count;
};

const odataFilter = (expr, odataToColumnMap) => {
  const ast = parseOdataExpr(expr);
  const nodeCount = countNodes(ast);
  if (nodeCount > MAX_FILTER_NODES) {
    throw Problem.user.unparseableODataExpression({
      reason: `Filter too complex (max ${MAX_FILTER_NODES} nodes)`
    });
  }
  // ... rest of function
};
```

#### 4. Result Size Limits

**Current:**
- `$top` parameter limits results (default: Infinity)
- No server-side cap found

**Recommended:**
```javascript
// server/lib/util/odata.js
const extractPaging = (query) => {
  const parsedLimit = parseInt(query.$top, 10);
  // Cap at 10,000 records per request
  const limit = Math.min(Number.isNaN(parsedLimit) ? 1000 : parsedLimit, 10000);
  // ...
};
```

#### 5. Audit Logging

**Implementation:**
```javascript
// server/lib/resources/odata.js
service.get(`${base}/:table`, endpoint.odata.json(async ({ Forms, Submissions, env }, { auth, params, query }) => {
  // Log OData access for audit
  await Audit.log(auth.actor(), 'odata.read', {
    projectId: params.projectId,
    formId: params.xmlFormId,
    table: params.table,
    filter: query.$filter,
    top: query.$top
  });
  // ... rest of endpoint
}));
```

---

## Summary and Recommendations

### Security Assessment: **LOW-MEDIUM RISK** ⚠️

| Threat | Risk Level | Mitigation Status |
|--------|------------|-------------------|
| SQL Injection | **NONE** | ✅ Slonik parameterized queries |
| Authorization Bypass | **NONE** | ✅ `auth.canOrReject()` enforced |
| Field Injection | **NONE** | ✅ Whitelist validation |
| DoS via Complex Queries | **LOW-MEDIUM** | ⚠️ Add query complexity limits |
| **Data Scraping** | **HIGH** | 🔴 **NO rate limiting** |
| **Automated Tool Abuse** | **MEDIUM** | 🔴 **NO rate limiting** |
| CRS False Positives | **NONE** | ✅ Rule 942290 exclusion is safe |

**Critical Gap:** No rate limiting on OData endpoints (login endpoints have rate limiting, but OData does not).

### Current CRS Exclusion: **SAFE TO KEEP** ✅

**Rule 942290** (SQLi detection) exclusion for `.svc` endpoints is **SAFE** because:
- Slonik ORM prevents SQL injection via parameterized queries
- OData filter is parsed into AST, not concatenated
- Only whitelisted fields are allowed
- No SQL injection possible despite SQL-like syntax

### Recommended Actions

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| **CRITICAL** | **Add WAF rate limiting for `.svc`** | **Prevents data scraping** | Low |
| **HIGH** | Keep CRS 942290 exclusion | Prevents false positives | None |
| **HIGH** | Add WAF rate limiting for `/submission` | Prevents submission spam | Low |
| **HIGH** | Add WAF rate limiting for `/formList` | Prevents OpenROSA abuse | Low |
| **MEDIUM** | Add server-side OIDC disable | Disables OData when not needed | Medium |
| **MEDIUM** | Add query complexity limits | Prevents DoS | Medium |
| **LOW** | Add app-level rate limiting | User-based limits | Medium |
| **LOW** | Add audit logging | Compliance monitoring | Low |
| **LOW** | Add IP-based restrictions | Defense in depth | Low |

### Rate Limiting Implementation Priority

**Immediate (WAF-Level):**
1. `crs_custom/30-odk-odata-rate-limiting.conf` - 100 req/min per IP for `.svc`
2. Stricter limit for `.svc/Submissions` - 50 req/min
3. Stricter limit for complex queries (>500 chars) - 10 req/min
4. Per-project rate limiting - 200 req/min

**Short-term (Application-Level):**
1. Add user-based rate limiting for OData queries
2. Add query complexity limits (max filter depth, max nodes)
3. Add result size caps (max `$top` value)

**Long-term (Monitoring):**
1. Audit logging for all OData access
2. Monitoring for bulk export patterns
3. Alerts for unusual OData activity

### Can OData Be Disabled?

**Short Answer:** Yes, but requires server-side changes.

**Options:**
1. **Quick Fix:** Disable OIDC (client-side OData already disabled)
2. **Server Fix:** Add middleware to return 404 when OIDC enabled
3. **Flexible Fix:** Add per-project `odata_enabled` flag

**Impact of Disabling:**
- ✅ Eliminates OData attack surface
- ❌ Breaks Power BI, Excel, pyODK, ruODK integration
- ❌ Breaks internal client submission table view (uses OData)

**Recommendation:**
If OData is not needed in your deployment:
1. Add server-side middleware to disable when OIDC enabled
2. Update client submission table to use REST API instead of OData
3. Monitor for any external tool integrations that may depend on OData

---

## Performance Considerations

### High-Load Endpoints

| Endpoint | Load | Response Size | WAF Impact |
|----------|------|---------------|------------|
| `.svc/Submissions` | **HIGH** | **LARGE** | Fast rules needed |
| `.svc/Submissions(:uuid)` | MEDIUM | MEDIUM | Standard |
| `.svc/($metadata)` | LOW | SMALL | Standard |

**Recommendations:**
1. Keep CRS 942290 exclusion (prevents false positives)
2. Monitor for OData abuse patterns
3. Consider per-project rate limiting

---

## Related Documentation

- **Modular Rate Limiting Design:** `docs/vg/vg-server/routes/vg-rate-limiting-design.md` (VG pattern approach)
- **Main WAF Inventory:** `docs/vg/modsecurity-waf-api-inventory.md`
- **Submission Endpoints:** `docs/vg/vg-server/routes/core-api-forms-submissions.md`
- **Entity Endpoints:** `docs/vg/vg-server/routes/core-api-entities-datasets.md`
- **CRS Exclusions:** `docs/vg/vg_modsecurity_crs_exclusions.md`
- **App User Auth:** `docs/vg/vg-server/routes/app-user-auth.md` (VG modular pattern reference)

---

## Verification Checklist

- [ ] All `.svc` endpoints documented
- [ ] CRS 942290 exclusion noted
- [ ] OData syntax examples provided
- [ ] Load levels marked (HIGH for feeds)
- [ ] Security risks assessed
- [ ] Current WAF config documented
- [ ] Client webapp usage documented
- [ ] SQL injection proof provided (Slonik)
- [ ] OData disable options documented
- [ ] Access restriction options documented
- [ ] Rate limiting options documented (Nginx, WAF, Application)
- [ ] Separation of concerns clarified
