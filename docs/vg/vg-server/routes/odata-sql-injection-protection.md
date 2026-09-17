# OData SQL Injection Protection & ModSecurity Hardening

> **Last Updated:** 2026-09-17
> **Purpose:** Complete analysis of SQL injection protections in OData endpoints and ModSecurity hardening recommendations

## Effective WAF policy (2026-09-17)

For GET requests on the exact Central OData route families below, including an
optional `/key/:token` prefix, the WAF removes `942290`:

```text
/v1/(key/:token/)?projects/:projectId/forms/:xmlFormId.svc[/...]
/v1/(key/:token/)?projects/:projectId/forms/:xmlFormId/draft.svc[/...]
/v1/(key/:token/)?projects/:projectId/datasets/:datasetName.svc[/...]
```

When `$filter` is present on those routes, it also removes `942100` and
`942151`. Rule `920100`, anomaly scoring, XSS, traversal, and all other CRS
rules remain active. Backend authentication and authorization apply to cookie,
Bearer, Basic, field-key, and `st` requests; the WAF tuning does not make SQL
injection impossible.

For PUT, PATCH, and DELETE under `/v1/`, only `911100` is removed, without
credential-shape gating. `949110` and `949111` remain active.

---

## Overview

This document analyzes:
1. **Application-level SQL injection protections** in OData implementation
2. **Current ModSecurity exclusions** and their security impact
3. **Attack surface analysis** for OData endpoints
4. **ModSecurity hardening recommendations** to minimize attack surface

---

## Executive Summary

### Security Assessment: **STRONG** ✅

| Protection Layer | Status | Effectiveness |
|-----------------|--------|---------------|
| **ORM (Slonik)** | ✅ Active | **HIGH** - Parameterized queries |
| **Field Whitelisting** | ✅ Active | **HIGH** - Only allowed fields |
| **AST Parsing** | ✅ Active | **HIGH** - Validated syntax |
| **Function Whitelist** | ✅ Active | **HIGH** - Only 7 functions |
| **ModSecurity SQLi** | ⚠️ **Scoped tuning** | `942290` on OData routes; `942100`/`942151` only with `$filter`; other rules active |
| **ModSecurity Protocol** | ✅ **Active** | `920100` remains active |

### Current WAF Exclusions

| Rule ID | Name | Excluded For | Risk Level |
|---------|------|--------------|------------|
| **942290** | SQLi Detection (NoSQL/MongoDB) | Exact OData GET routes | Scoped for protocol syntax |
| **942100** | Libinjection SQLi | OData routes with `$filter` | Scoped for filter syntax |
| **942151** | SQL function SQLi | OData routes with `$filter` | Scoped for filter syntax |
| **920100** | Protocol Enforcement | All requests | Remains active |

**Conclusion:** Application-level parsing, field validation, and parameterized
queries provide defense in depth. WAF tuning is narrowly scoped, and the
remaining CRS rules continue to inspect requests; no layer should be described
as making SQL injection impossible.

---

## Application-Level Protections

### 1. Slonik ORM Parameterized Queries ✅

**File:** `server/lib/data/odata-filter.js:10`

**Protection:** All SQL queries use Slonik's `sql` template literal with parameterization.

```javascript
const { sql } = require('slonik');

// Example from odataFilter():
const equality = (node) => {
  const left = op(node.value.left);
  const right = op(node.value.right);

  // Parameterized comparison - NO string concatenation
  return booleanOp(sql`${left} IS NOT DISTINCT FROM ${right}`);
};
```

**Why This Prevents SQL Injection:**
- Slonik uses prepared statements with bind parameters
- User input is NEVER concatenated into SQL strings
- All values are properly escaped based on their type
- PostgreSQL driver handles parameter binding

**Proof:**
```javascript
// SAFE - Parameterized (actual implementation)
sql`${left} < ${right}`

// UNSAFE - String concatenation (NOT used)
sql`${left} < ${userInput}`  // This would be vulnerable!
```

---

### 2. Field Whitelisting ✅

**File:** `server/lib/data/odata-filter.js:66-71`

**Protection:** Only fields in `odataToColumnMap` can be queried.

```javascript
const op = (node) => {
  if (node.type === 'FirstMemberExpression' || node.type === 'RootExpression') {
    // Check if field is in whitelist
    if (odataToColumnMap.has(node.raw)) {
      // SAFE - Field is whitelisted
      return sql.identifier(odataToColumnMap.get(node.raw).split('.'));
    } else {
      // BLOCKED - Unknown field rejected
      throw Problem.internal.unsupportedODataField({ at: node.position, text: node.raw });
    }
  }
};
```

**Attack Prevented:**
```bash
# ATTACK ATTEMPT - Arbitrary field access
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=password eq 'admin'

# RESULT - Rejected with 500 error
Problem.internal.unsupportedODataField({ text: 'password' })
```

---

### 3. AST Parsing & Validation ✅

**File:** `server/lib/data/odata-filter.js:14-20`

**Protection:** OData expressions are parsed into an AST by `odata-v4-parser` library.

```javascript
const odataParser = require('odata-v4-parser');

const parseOdataExpr = expr => {
  try {
    // Parse OData expression into Abstract Syntax Tree
    return odataParser.filter(expr);
  } catch (ex) {
    // Invalid syntax rejected
    throw Problem.user.unparseableODataExpression({ reason: ex.message });
  }
};
```

**Attack Prevented:**
```bash
# ATTACK ATTEMPT - Invalid syntax
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=1; DROP TABLE--

# RESULT - Parser throws before reaching database
Problem.user.unparseableODataExpression({ reason: 'syntax error' })
```

---

### 4. Function Whitelisting ✅

**File:** `server/lib/data/odata-filter.js:33-45`

**Protection:** Only 7 OData functions are allowed.

```javascript
const extractFunctions = ['year', 'month', 'day', 'hour', 'minute', 'second'];

const methodCall = (node) => {
  const fn = node.value.method;
  const params = node.value.parameters;

  if (extractFunctions.includes(fn)) {
    // SAFE - Function is whitelisted
    return sql`extract(${sql.identifier([fn])} from ${op(params[0])})`;
  } else if (fn === 'now') {
    return sql`now()`;
  } else {
    // BLOCKED - Unknown function rejected
    throw Problem.internal.unsupportedODataExpression({
      at: node.position,
      type: node.type,
      text: node.raw
    });
  }
};
```

**Allowed Functions:**
- `year()`, `month()`, `day()` - Date extraction
- `hour()`, `minute()`, `second()` - Time extraction
- `now()` - Current timestamp

**Attack Prevented:**
```bash
# ATTACK ATTEMPT - Function injection
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=version() = '1'

# RESULT - Function rejected
Problem.internal.unsupportedODataExpression({ text: 'version()' })
```

---

### 5. Type Validation ✅

**File:** `server/lib/data/odata-filter.js:72-78`

**Protection:** Literals are validated and properly escaped.

```javascript
} else if (node.type === 'Literal') {
  // for some reason string literals come with their quotes
  return (node.raw === 'null') ? null
    : (/^'.*'$/.test(node.raw)) ? node.raw.slice(1, node.raw.length - 1)
      : node.raw;
}
```

**Protection Provided:**
- String literals have quotes removed
- Null literals are handled safely
- Numeric literals are preserved
- No code execution possible

---

### 6. OrderBy Validation ✅

**File:** `server/lib/data/odata-filter.js:152-177`

**Protection:** `$orderby` parameter validates both field names and direction.

```javascript
const odataOrderBy = (expr, odataToColumnMap, stableOrderColumn = null) => {
  const clauses = expr.split(',').map((exp) => {
    const [col, order] = exp.trim().split(/\s+/);

    // validate field
    if (!odataToColumnMap.has(col))
      throw Problem.internal.unsupportedODataField({ text: col });

    // validate order (asc or desc)
    if (order && !order?.toLowerCase().match(/^(asc|desc)$/))
      throw Problem.internal.unsupportedODataField({ text: order });

    return sql`${sql.identifier(odataToColumnMap.get(col).split('.'))} ${sqlOrder}`;
  });
};
```

**Attack Prevented:**
```bash
# ATTACK ATTEMPT 1 - Unknown field
GET /v1/projects/1/forms/basic.svc/Submissions?$orderby=password

# RESULT - Field rejected
Problem.internal.unsupportedODataField({ text: 'password' })

# ATTACK ATTEMPT 2 - SQL injection in direction
GET /v1/projects/1/forms/basic.svc/Submissions?$orderby=id;DROP TABLE--

# RESULT - Direction validation fails
Problem.internal.unsupportedODataField({ text: ';DROP TABLE--' })
```

---

## Current ModSecurity Exclusions

### Exclusion Configuration

**File:** `crs_custom/20-odk-odata-exclusions.conf`

```nginx
# ODK Central OData endpoints (Submissions)
# Central uses OData-style query params like $filter, $orderby, $top, etc.
# CRS can false-positive these (e.g. $filter flagged as SQLi keyword).
#
# We keep this scoped to .svc/ endpoints and only for requests that appear to
# match Central's documented OData GET route families. Credential handling is
# performed by the backend and is deliberately not part of this WAF match.
SecRule REQUEST_METHOD "@streq GET" "id:1000201,phase:1,pass,nolog,chain"
  SecRule REQUEST_FILENAME "@rx ^/v1/(?:key/[^/]+/)?projects/[0-9]+/(?:forms/[^/]+(?:\.svc|/draft\.svc)|datasets/[^/]+\.svc)(?:/.*)?$" \
    "t:none,ctl:ruleRemoveById=942290"

SecRule REQUEST_METHOD "@streq GET" "id:1000202,phase:1,pass,nolog,chain"
  SecRule REQUEST_FILENAME "@rx ^/v1/(?:key/[^/]+/)?projects/[0-9]+/(?:forms/[^/]+(?:\.svc|/draft\.svc)|datasets/[^/]+\.svc)(?:/.*)?$" "chain"
    SecRule ARGS_NAMES "@streq $filter" \
      "t:none,ctl:ruleRemoveById=942100,ctl:ruleRemoveById=942151"
```

### What Each Exclusion Does

#### Rule 942290 - SQL Injection Detection

**From [OWASP CRS](https://github.com/coreruleset/coreruleset/blob/main/rules/REQUEST-942-APPLICATION-ATTACK-SQLI.conf):**

- **Purpose:** Detects MongoDB/NoSQL injection patterns
- **Patterns:** `$in`, `$ne`, `$gt`, `$lt`, `$and`, `$or`, `$not` operators
- **Why Scoped:** OData uses operators and argument names that can resemble
  injection syntax. The exception is restricted to recognized OData GET paths.

**False Positive Examples:**
```bash
# Legitimate OData - triggers 942290 due to $in-like syntax
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=status eq 'submitted'

# Legitimate OData - triggers 942290 due to $or
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=status eq 'submitted' or status eq 'pending'

# Legitimate OData - triggers 942290 due to $and
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=age ge 18 and age lt 65
```

**Security Impact:** Reduced WAF coverage for this rule on recognized OData
requests. Slonik parameterization and OData validation provide additional
defense in depth; they do not make SQL injection impossible.

#### Rule 920100 - Protocol Enforcement

**From [OWASP CRS](https://github.com/coreruleset/coreruleset/blob/main/rules/REQUEST-920-PROTOCOL-ENFORCEMENT.conf):**

- **Purpose:** Validates HTTP request line format
- **Current status:** Active. Complex or encoded OData requests remain subject
  to protocol validation.

**Security Impact:** Protocol inspection remains active for OData requests.

### Scope of Exclusions

Exclusions are **tightly scoped** to minimize attack surface:

| Scope Condition | Value | Purpose |
|----------------|-------|---------|
| **Method** | `GET` only | Only read operations |
| **Path** | Exact form, draft-form, and dataset `.svc` families (optional `/key/:token`) | Only Central OData endpoints |
| **Credentials** | Not matched by WAF | Backend authenticates cookie/Bearer/Basic/field-key/`st` |
| **Phase** | `phase:1` | Before body parsing |

**What This Means:**
- ❌ No exclusions for POST/PUT/DELETE
- ❌ No exclusions for non-OData endpoints
- ✅ Requests using any backend-supported credential transport reach backend auth

---

## Attack Surface Analysis

### SQL injection: application-level controls

| Attack Vector | Protection | Status |
|---------------|------------|--------|
| String concatenation | Slonik parameterization | ✅ Blocked |
| Field injection | Whitelist validation | ✅ Blocked |
| Function injection | Function whitelist (7 functions) | ✅ Blocked |
| Operator injection | AST parsing validation | ✅ Blocked |
| Comment injection | Parser syntax validation | ✅ Blocked |
| UNION injection | Slonik parameterization | ✅ Blocked |

**Proof of Protection:**

```javascript
// All user input goes through this flow:
userInput → parseOdataExpr() → AST → op() → sql.identifier() → Slonik → PostgreSQL

// At each step:
// 1. parseOdataExpr() - Validates syntax, throws on error
// 2. op() - Validates node type, throws on unknown
// 3. sql.identifier() - Safely escapes identifier
// 4. Slonik - Parameterizes all values
```

### NoSQL/MongoDB injection: application context

**Note:** Rule 942290 is for **MongoDB/NoSQL** injection, not SQL injection.

**ODK Central uses PostgreSQL**, not MongoDB. The OData syntax that triggers 942290:
- `eq` (equals), `ne` (not equals), `gt` (greater than), `lt` (less than)
- `and`, `or`, `not` operators
- These are **OData operators**, not MongoDB operators

**Why This is Safe:**
- OData operators are parsed into SQL by `odataFilter()`
- Resulting SQL uses Slonik parameterization
- No MongoDB NoSQL syntax reaches the database

---

## ModSecurity Hardening Recommendations

### Current State Assessment

**Current exclusions are narrowly scoped:** ✅

| Aspect | Status | Notes |
|--------|--------|-------|
| Scope | ✅ Good | Exact OData GET route families |
| Number of rules | ✅ Good | Only documented false-positive rules are scoped |
| Layer | ✅ Defense in depth | Backend validation and remaining CRS rules stay active |

### Current policy: keep the scoped exceptions

**Reason:**
1. Application-layer protections are strong (Slonik + whitelisting)
2. Exclusions are tightly scoped (GET only, exact OData routes)
3. Application parsing and parameterization reduce SQL injection risk but do not
   justify an absolute guarantee
4. Disabling would block legitimate traffic

### Additional Hardening Options

While current protections are strong, additional ModSecurity rules can provide defense-in-depth:

#### Option 1: OData-Specific Validation Rules (Optional)

**File:** `crs_custom/25-odk-validation.conf`

```nginx
# ============================================================================
# OData-Specific Validation (Defense-in-Depth)
# These rules validate OData syntax WITHOUT interfering with legitimate queries
# ============================================================================

# Validate $filter parameter length (DoS prevention)
SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2501,phase:2,deny,status:414,status:413,msg:'OData filter too long', \
    SecRule ARGS_NAMES:\$filter "@gt 2000"

# Validate $orderby parameter (field names only)
SecRule REQUEST_URI "@rx \.svc/.*\$orderby=" \
    "id:2502,phase:2,deny,status:400,msg:'Invalid OData orderby parameter', \
    SecRule ARGS:\$orderby "!@rx ^[a-zA-Z0-9_/,_ -]+$"

# Validate $select parameter (field names only, comma-separated)
SecRule REQUEST_URI "@rx \.svc/.*\$select=" \
    "id:2503,phase:2,deny,status:400,msg:'Invalid OData select parameter', \
    SecRule ARGS:\$select "!@rx ^[a-zA-Z0-9_/,_ -]+$"

# Validate $top parameter (numeric only)
SecRule REQUEST_URI "@rx \.svc/.*\$top=" \
    "id:2504,phase:2,deny,status:400,msg:'Invalid OData top parameter', \
    SecRule ARGS:\$top "!@rx ^[0-9]+$"

# Validate $skip parameter (numeric only)
SecRule REQUEST_URI "@rx \.svc/.*\$skip=" \
    "id:2505,phase:2,deny,status:400,msg:'Invalid OData skip parameter', \
    SecRule ARGS:\$skip "!@rx ^[0-9]+$"

# Block common injection patterns in OData (defense-in-depth)
# These patterns should never appear in legitimate OData queries
SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2506,phase:2,deny,status:400,msg:'OData injection pattern blocked', \
    SecRule ARGS:\$filter "@rx (union|select|insert|update|delete|drop|create|alter|grant|revoke)" \
    "t:lowercase,chain"
    SecRule ARGS:\$filter "!@rx \\b(eq|ne|gt|ge|lt|le|and|or|not)\\b"

# Block OData function calls other than whitelisted ones
SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2507,phase:2,deny,status:400,msg:'OData function not allowed', \
    SecRule ARGS:\$filter "@rx (\\(|\\))" \
    "t:lowercase,chain"
    SecRule ARGS:\$filter "!@rx \\b(year|month|day|hour|minute|second|now)\\(" \
    "t:lowercase"
```

**Note:** These rules provide defense-in-depth but are NOT required for security since application-layer protections are already strong.

---

#### Historical option: reduce exclusion scope (superseded)

**Historical exclusion:**
```nginx
# Excludes 942290 and 920100 for ALL .svc requests with session cookie
SecRule REQUEST_URI "@endsWith .svc" \
    "ctl:ruleRemoveById=942290"
```

**More Targeted Exclusion:**
```nginx
# Only exclude 942290 for specific OData operators (reduces scope)
SecRule REQUEST_URI "@rx \.svc/.*\$filter=(.*)(eq|ne|gt|ge|lt|le|and|or)" \
    "id:1001,phase:2,pass,nolog,ctl:ruleRemoveById=942290"

# Historical 920100 exclusion; do not use in the effective policy
SecRule REQUEST_URI "@rx \.svc/(?:Submissions|Entities)" \
    "SecRule REQUEST_HEADERS:Cookie '@rx (__Host-session=|__csrf=)' \
    "ctl:ruleRemoveById=920100"
```

**Trade-off:**
- ✅ More targeted (only excludes when OData operators are present)
- ❌ More complex to maintain
- ❌ May miss edge cases

**Status:** Superseded by the exact route and `$filter`-scoped policy at the top
of this document.

---

#### Option 3: Add Request Body Validation (For POST/PUT)

**Current:** Exclusions only apply to GET requests

**Future-proofing:** If OData adds POST/PUT support:

```nginx
# Validate request body for OData endpoints (future-proofing)
SecRule REQUEST_URI "@rx \.svc/" \
    "id:2508,phase:2,deny,status:400,msg:'Invalid OData content type', \
    SecRule REQUEST_HEADERS:Content-Type "!@rx (application/json|application/atomsvc|application/xml)"
```

---

### Monitoring Recommendations

#### 1. Audit Logging for Failed OData Requests

```nginx
# Log blocked OData requests for analysis
SecRule REQUEST_URI "@rx \.svc/" \
    "id:2599,phase:2,pass,nolog, \
    SecRule RESPONSE_STATUS "@streq 400", \
    msg:'OData request blocked - audit logging', \
    ctl:auditLogEngine=On"
```

#### 2. Alert on Suspicious Patterns

```nginx
# Alert on repeated OData SQLi-like patterns (may indicate probing)
SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2600,phase:1,pass,nolog, \
    SecRule ARGS:\$filter "@rx (union|select|insert|update|delete|drop)" \
    "t:lowercase,msg:'Potential OData injection attempt detected'"
```

#### 3. Track OData Usage Patterns

```nginx
# Track OData endpoint usage for monitoring
SecRule REQUEST_URI "@rx \.svc/" \
    "id:2601,phase:1,pass,nolog,initcol:ip.odata_tracker, \
    setvar:ip.odata_tracker_counter=+1"
```

---

## Defense-in-Depth Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OData SQL Injection Defense                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐  │
│  │ ModSecurity │    │ Application  │    │   Database (Slonik) │  │
│  │   WAF        │    │   Layer      │    │      ORM           │  │
│  └──────┬──────┘    └──────┬───────┘    └──────────┬──────────┘  │
│         │                   │                        │              │
│         │                   │                        │              │
│  ┌──────▼───────────────────▼────────────────────────▼──────────┐  │
│  │                 PROTECTION LAYERS                             │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ Layer 1: ModSecurity (WAF)                                   │  │
│  │   - Protocol validation (920100 active)                     │  │
│  │   - Scoped SQLi tuning (942290; filter rules as documented) │  │
│  │   - Can add: Parameter length, syntax validation             │  │
│  │                                                             │  │
│  │ Layer 2: Application (server/lib/data/odata-filter.js)      │  │
│  │   - AST parsing (odata-v4-parser) ✅ STRONG                │  │
│  │   - Field whitelisting (odataToColumnMap) ✅ STRONG         │  │
│  │   - Function whitelist (7 functions) ✅ STRONG              │  │
│  │   - Type validation ✅ STRONG                                 │  │
│  │                                                             │  │
│  │ Layer 3: ORM (Slonik)                                       │  │
│  │   - Parameterized queries ✅ STRONG                           │  │
│  │   - No string concatenation ✅ STRONG                         │  │
│  │   - Bind parameters ✅ STRONG                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ✅ SQL injection: reduced by layered controls                  │
│  ✅ NoSQL injection: no MongoDB query layer                     │
│  ✅ Field injection: constrained by whitelist validation         │
│  ✅ Function injection: constrained by function whitelist       │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Historical threat modeling (status wording superseded)

### Attack Scenario 1: SQL Injection via $filter

**Attacker Input:**
```bash
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=id=1;DROP TABLE users--
```

**Defense Layers:**
1. **ModSecurity:** 942290 is tuned only on recognized OData routes; other CRS rules remain active
2. **Parser:** ✅ `odata-v4-parser` throws syntax error
3. **Application:** ✅ Never reaches database

**Result:** **BLOCKED** - Parser rejects before database

---

### Attack Scenario 2: Field Injection via $filter

**Attacker Input:**
```bash
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=password eq 'admin'
```

**Defense Layers:**
1. **ModSecurity:** 942290 is tuned only on recognized OData routes; other CRS rules remain active
2. **Whitelist:** ✅ `odataToColumnMap` doesn't contain 'password'
3. **Application:** ✅ Throws `unsupportedODataField`

**Result:** **BLOCKED** - Whitelist rejects unknown field

---

### Attack Scenario 3: Function Injection via $filter

**Attacker Input:**
```bash
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=eval('malicious code')
```

**Defense Layers:**
1. **ModSecurity:** 942290 is tuned only on recognized OData routes; other CRS rules remain active
2. **Parser:** ✅ `odata-v4-parser` throws syntax error
3. **Function Check:** ✅ `extractFunctions` doesn't include 'eval'
4. **Application:** ✅ Throws `unsupportedODataExpression`

**Result:** **BLOCKED** - Function whitelist rejects

---

### Attack Scenario 4: UNION Injection via $filter

**Attacker Input:**
```bash
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=id=1 UNION SELECT password FROM users
```

**Defense Layers:**
1. **ModSecurity:** 942290 is tuned only on recognized OData routes; other CRS rules remain active
2. **Parser:** ✅ `odata-v4-parser` doesn't support UNION
3. **Slonik:** ✅ Parameterized anyway (wouldn't work)

**Result:** **BLOCKED** - Parser rejects invalid syntax

---

## Comparison: With vs Without ModSecurity

| Attack | Without ModSecurity | With ModSecurity (Current) | With ModSecurity (Enhanced) |
|--------|-------------------|----------------------------|----------------------------|
| SQL injection via $filter | ✅ App validation | ⚠️ Scoped WAF tuning plus app validation | ✅ App validation |
| Field injection | ✅ App validation | ✅ App validation and remaining CRS rules | ✅ App validation |
| Function injection | ✅ App validation | ✅ App validation and remaining CRS rules | ✅ App validation |
| DoS via large query | ❌ Not protected | ⚠️ Excluded | ✅ Can add rules |
| Invalid syntax | ✅ Blocked by app | ⚠️ Excluded | ✅ Can add rules |

**Conclusion:** ModSecurity provides protocol and attack-pattern inspection in
addition to application-layer parsing and parameterization. The scoped OData
tuning accommodates known syntax while retaining the remaining CRS controls.

---

## Final Recommendations

### Immediate Actions (Required)

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| **NONE** | Keep current exclusions | None | No action needed |

### Optional Hardening (Nice to Have)

| Priority | Action | Effort | Impact |
|----------|--------|--------|--------|
| LOW | Add OData parameter length limits | Low | Prevents DoS |
| LOW | Add OData syntax validation | Low | Better error messages |
| LOW | Add monitoring/alerting | Low | Detection of probing |

### What NOT to Do

| Action | Why Not |
|--------|---------|
| Apply 942290 to OData argument names | Blocks legitimate `$`-prefixed OData queries |
| Disable 920100 | Unnecessary; valid raw and encoded OData requests pass with it active |
| Remove field whitelisting | Would weaken security |
| Remove AST parsing | Would weaken security |

---

## Related Documentation

- **OData Endpoints:** `docs/vg/vg-server/routes/odata-endpoints.md`
- **CRS Exclusions:** `docs/vg/vg_modsecurity_crs_exclusions.md`
- **WAF Inventory:** `docs/vg/modsecurity-waf-api-inventory.md`
- **ModSecurity Config:** `docs/vg/vg_modsecurity.md`
- **App User Auth:** `docs/vg/vg-server/routes/app-user-auth.md` (VG modular pattern)

---

## Sources

- [OWASP CRS REQUEST-942-APPLICATION-ATTACK-SQLI.conf](https://github.com/coreruleset/coreruleset/blob/main/rules/REQUEST-942-APPLICATION-ATTACK-SQLI.conf)
- [OWASP CRS REQUEST-920-PROTOCOL-ENFORCEMENT.conf](https://github.com/coreruleset/coreruleset/blob/main/rules/REQUEST-920-PROTOCOL-ENFORCEMENT.conf)
- [OWASP CRS Changelog](https://github.com/coreruleset/coreruleset/wiki/CRSv4-Changelog)
- [Rule 920100 PCRE Limits Issue](https://github.com/coreruleset/coreruleset/issues/3640)
- [Rule 942290 False Positives](https://github.com/coreruleset/coreruleset/issues/4349)

---

## Verification Checklist

- [ ] Application-layer protections documented
- [ ] Slonik parameterization explained
- [ ] Field whitelisting explained
- [ ] AST parsing explained
- [ ] Function whitelisting explained
- [ ] Current ModSecurity exclusions analyzed
- [ ] Attack surface assessed
- [ ] Hardening recommendations provided
- [ ] Defense-in-depth architecture documented
- [ ] Threat modeling completed
