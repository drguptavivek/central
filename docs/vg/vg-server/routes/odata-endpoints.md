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

## Security Considerations

### OData Injection Risks

**SQL Injection:** LOW risk
- Backend uses parameterized queries (Slonik)
- OData queries are parsed, not concatenated

**DoS via Complex Queries:** MEDIUM risk
- OData supports nested `$filter` expressions
- Consider query complexity limits

**Data Scraping:** MEDIUM risk
- OData allows full data export
- Consider rate limiting per project

### Current Protections

1. **Authentication required:** Field Key or Bearer token
2. **Authorization checked:** Can only query accessible data
3. **Parameterized queries:** No SQL injection possible
4. **WAF exclusion:** Only disables false positive detection

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

- **Main WAF Inventory:** `docs/vg/modsecurity-waf-api-inventory.md`
- **Submission Endpoints:** `docs/vg/vg-server/routes/core-api-forms-submissions.md`
- **Entity Endpoints:** `docs/vg/vg-server/routes/core-api-entities-datasets.md`
- **CRS Exclusions:** `docs/vg/vg_modsecurity_crs_exclusions.md`

---

## Verification Checklist

- [ ] All `.svc` endpoints documented
- [ ] CRS 942290 exclusion noted
- [ ] OData syntax examples provided
- [ ] Load levels marked (HIGH for feeds)
- [ ] Security risks assessed
- [ ] Current WAF config documented
