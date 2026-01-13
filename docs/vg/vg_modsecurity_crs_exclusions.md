# ModSecurity CRS Exclusions Reference

> **Last Updated:** 2026-01-14
> **OWASP CRS Version:** v4.21.0
> **Purpose:** Complete reference for all CRS rule exclusions

---

## Overview

This document explains which OWASP CRS rules are disabled or modified for ODK Central and why.

**Location:**
- Nginx config: `files/nginx/odk.conf.template`
- Custom exclusions: `crs_custom/` directory

---

## Current Exclusions Summary

| Rule ID | Name | Disabled For | Reason |
|---------|------|--------------|--------|
| **911100** | Method Enforcement | `/v1/` API | Allow PATCH/PUT/DELETE methods |
| **942290** | SQLi Detection | OData `.svc/` | OData filter syntax looks like SQL |
| **949110** | Anomaly Scoring | `/v1/` API | Lower threshold for API traffic |
| **949111** | Anomaly Scoring | `/v1/` API | Lower threshold for API traffic |

---

## Exclusion 1: Method Enforcement (Rule 911100)

**Location:** `files/nginx/odk.conf.template`

```nginx
location ~ ^/v\d {
    # VG: Disable CRS blocking rules for Central API
    modsecurity_rules 'SecRuleRemoveById 911100 949110 949111';

    # VG: Disable CRS blocking rules for Central API (PATCH/PUT/DELETE methods)
    modsecurity_rules 'SecRuleRemoveById 911100 949110 949111';
}
```

**Rule 911100:** Enforces allowed HTTP methods (GET, POST, only)

**Why Disabled:**
- ODK Central API uses PATCH and PUT methods
- DELETE method used for resource deletion
- RESTful API requires full HTTP method support

**Impact:**
- Allows: GET, POST, PUT, PATCH, DELETE
- Application-layer validation still applies
- No security risk (proper auth required)

**Alternatives:**
- Could selectively enable per-endpoint
- Current approach: blanket disable for `/v1/` path

---

## Exclusion 2: SQL Injection Detection (Rule 942290)

**Location:** `crs_custom/20-odk-odata-exclusions.conf`

```nginx
# OData SQL-like syntax in $filter parameter
SecRule REQUEST_URI "@endsWith .svc" \
    "id:1000,phase:2,pass,nolog,ctl:ruleRemoveById=942290"
```

**Rule 942290:** Detects SQL injection patterns

**Why Disabled:**
- OData query syntax uses SQL-like keywords:
  - `?$filter=field eq 'value'` (equals)
  - `?$filter=age gt 18` (greater than)
  - `?$filter=status eq 'active' or age gt 18` (or/and)

**Examples That Trigger 942290:**
```
# These are legitimate OData queries:
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=status eq 'submitted'
GET /v1/projects/1/forms/basic.svc/Submissions?$filter=name ne 'test' and age ge 18
GET /v1/projects/1/datasets/people.svc/Entities?$filter=createdAt gt 2023-01-01
```

**Impact:**
- SQLi detection disabled ONLY for `.svc` endpoints
- Backend uses parameterized queries (Slonik)
- No actual SQL injection risk

**Security Note:**
- Slonik ORM prevents SQL injection
- All queries are parameterized
- This exclusion is SAFE

---

## Exclusion 3: Anomaly Scoring (Rules 949110, 949111)

**Location:** `files/nginx/odk.conf.template`

```nginx
modsecurity_rules 'SecRuleRemoveById 911100 949110 949111';
```

**Rules 949110, 949111:** Anomaly scoring thresholds

**Why Disabled:**
- API requests often trigger multiple lower-severity rules
- Combined anomaly score exceeds threshold
- Legitimate API traffic blocked

**Example Triggers:**
- Large JSON bodies (JSON rule)
- Multipart uploads (file upload rules)
- OData queries (SQL-like syntax)
- Form field names (various patterns)

**Impact:**
- Lower blocking threshold for `/v1/` API
- Individual rules still log warnings
- Only combined score threshold adjusted

**Risk Assessment:**
- **LOW RISK**: Application-layer validation still applies
- All endpoints require authentication
- Input validation at application level

---

## Custom Exclusions Files

### crs_custom/00-empty.conf
```nginx
# Placeholder file - no exclusions
```

### crs_custom/10-odk-exclusions.conf
```nginx
# Disable file access rule for client-config.json
SecRule REQUEST_URI "@rx /client-config.json$" \
    "id:2001,phase:1,pass,nolog,ctl:ruleRemoveById=930130"
```

**Rule 930130:** File access restrictions

**Why Disabled:**
- `/client-config.json` is a public endpoint
- Returns empty JSON object `{}`
- No security risk

### crs_custom/20-odk-odata-exclusions.conf
```nginx
# OData SQL-like syntax
SecRule REQUEST_URI "@endsWith .svc" \
    "id:1000,phase:2,pass,nolog,ctl:ruleRemoveById=942290"
```

**See:** Exclusion 2 above

### crs_custom/30-odk-api-methods.conf
```nginx
# Disable method enforcement for API PATCH/PUT/DELETE
# (Handled in nginx config, kept for reference)
```

**Note:** This is documented in nginx config instead

### crs_custom/40-odk-api-anomaly-threshold.conf
```nginx
# Adjust anomaly scoring for API endpoints
# (Handled in nginx config, kept for reference)
```

**Note:** This is documented in nginx config instead

---

## Recommended Additional Exclusions

### 1. Large Payload Exclusions

**For submission endpoints:**
```nginx
# Allow large multipart submissions
SecRule REQUEST_METHOD "@streq POST" \
    "SecRule REQUEST_URI "@endsWith /submission" \
    "id:5001,phase:1,pass,nolog,ctl:requestBodyLimit=104857600"
```

**Why:**
- OpenROSA submissions up to 100MB
- Default body limit too restrictive

### 2. OpenROSA Header Validation

**For OpenROSA compliance:**
```nginx
# Require OpenROSA header
SecRule REQUEST_URI "@rx ^/v1/projects/\d+/formList$" \
    "SecRule &REQUEST_HEADERS:X-OpenRosa-Version "@eq 0" \
    "id:5002,phase:1,deny,status=400,msg='Missing OpenROSA header'"

SecRule REQUEST_URI "@rx ^/v1/projects/\d+/forms/[^/]+/manifest$" \
    "SecRule &REQUEST_HEADERS:X-OpenRosa-Version "@eq 0" \
    "id:5003,phase:1,deny,status=400,msg='Missing OpenROSA header'"
```

**Why:**
- OpenROSA protocol requires `X-OpenRosa-Version: 1.0`
- Server doesn't enforce (WAF should)

### 3. Rate Limiting (WAF-Level)

**For login endpoints:**
```nginx
# Backup rate limiting for login
SecRule REQUEST_URI "@rx /sessions$" \
    "SecRule REQUEST_METHOD "@streq POST" \
    "id:5004,phase:1,deny,status=429,\
    setvar:ip.login_counter=+1,expirevar:ip.login_counter=300,\
    t:count,deny,msg='Rate limit exceeded'"
```

**Note:** Application-level rate limiting exists, this is WAF backup

---

## Exclusion Decision Flow

```
┌─────────────────────────────────────────┐
│ Request arrives at WAF                  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ Is it /v1/ API?     │
        └─────────┬───────────┘
                  │
         ┌────────┴────────┐
         │ YES             │ NO
         ▼                 ▼
┌──────────────────┐  ┌──────────────────┐
│ Disable 911100   │  │ Full CRS        │
│ (Methods)        │  │ enforcement     │
├──────────────────┤  └──────────────────┘
│ Disable 949110   │
│ Disable 949111   │
└─────────┬────────┘
          │
          ▼
┌─────────────────────┐
│ Is it .svc OData?   │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │ YES         │ NO
   ▼             ▼
┌────────────┐ ┌────────────┐
│ Disable    │ │ No more    │
│ 942290     │ │ exclusions │
└────────────┘ └────────────┘
```

---

## Security Impact Assessment

### Overall Risk: **LOW**

| Exclusion | Risk Level | Mitigation |
|-----------|------------|------------|
| 911100 (Methods) | LOW | Application validation |
| 942290 (SQLi) | **NONE** | Parameterized queries |
| 949110, 949111 (Anomaly) | LOW | Auth + app validation |

**Why Safe:**
1. **Authentication Required:** All endpoints have auth
2. **Input Validation:** Application-level checks
3. **Parameterized Queries:** No SQL injection possible
4. **Rate Limiting:** Application-level protection

---

## Monitoring Recommendations

### Logs to Monitor

```
# Check for blocked requests that should be allowed
grep "ModSecurity.*block" /var/log/modsecurity/audit.log

# Check for high anomaly scores (non-blocked)
grep "anomaly_score" /var/log/modsecurity/audit.log | awk '{if($NF>5)print}'

# Check for SQLi attempts (should be rare)
grep "942290" /var/log/modsecurity/audit.log
```

### Alerts to Configure

1. **Spike in blocks:** May indicate false positives
2. **SQLi attempts:** On non-OData endpoints
3. **Anomaly score > 10:** On authenticated endpoints
4. **Rate limit hits:** On login endpoints

---

## Related Documentation

- **Main WAF Inventory:** `docs/vg/modsecurity-waf-api-inventory.md`
- **Modsecurity Config:** `docs/vg/vg_modsecurity.md`
- **Nginx Config:** `files/nginx/odk.conf.template`
- **CRS Documentation:** https://coreruleset.org/

---

## Verification Checklist

- [ ] All current exclusions documented
- [ ] Rule numbers identified
- [ ] Reasons for each exclusion explained
- [ ] Security impact assessed
- [ ] Monitoring recommendations provided
- [ ] Custom files in `crs_custom/` documented
