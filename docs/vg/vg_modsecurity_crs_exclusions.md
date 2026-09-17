# ModSecurity CRS Exclusions Reference

> **Last Updated:** 2026-09-17
> **OWASP CRS Version:** v4.25.1 (image-pinned)
> **Purpose:** Complete reference for all CRS rule exclusions

---

## Overview

This document explains which OWASP CRS rules are disabled or modified for ODK Central and why.

**Location:**
- Nginx config: `files/nginx/odk.conf.template`
- Custom exclusions: `crs_custom/` directory

## Effective policy (2026-09-17)

Only the following request-scoped exceptions are active:

| Request | Rules removed | Rules retained |
|---|---|---|
| GET on `/v1/(key/:token/)?projects/:projectId/forms/:xmlFormId.svc[/...]`, `/v1/(key/:token/)?projects/:projectId/forms/:xmlFormId/draft.svc[/...]`, or `/v1/(key/:token/)?projects/:projectId/datasets/:datasetName.svc[/...]` | `942290` | `920100` and every other CRS rule |
| The same OData routes when `$filter` is present | `942100`, `942151` | `942290` is already removed; `920100`, anomaly, XSS, traversal, and all other CRS rules remain |
| PUT, PATCH, or DELETE under `/v1/` | `911100` | `949110`, `949111`, and every other CRS rule |

The OData exceptions do not require a session cookie. Cookie, Bearer, Basic,
field-key, and `st` requests reach Central's backend authentication and
authorization checks. These exceptions tune false positives in recognized
protocol syntax; they are not a complete SQL injection control.

---

## Current Exclusions Summary

| Rule ID | Name | Disabled For | Reason |
|---------|------|--------------|--------|
| **911100** | Method Enforcement | PUT/PATCH/DELETE under `/v1/` | Central REST methods |
| **942290** | SQLi Detection | Exact documented OData GET routes | OData protocol syntax |
| **942100** | Libinjection SQLi | Those OData routes when `$filter` is present | OData filter syntax |
| **942151** | SQL function SQLi | Those OData routes when `$filter` is present | OData filter syntax |

---

## Exclusion 1: Method Enforcement (Rule 911100)

For PUT, PATCH, and DELETE requests under `/v1/`, `crs_custom/30-odk-api-methods.conf`
removes only `911100`. It is not gated on a cookie or any other credential
shape. `949110`, `949111`, and all other CRS rules remain active.

## Exclusion 2: OData syntax rules (942290, 942100, 942151)

`crs_custom/20-odk-odata-exclusions.conf` applies only to GET requests on the
three documented form, draft-form, and dataset `.svc` route families. The
optional `/key/:token` prefix is part of those families. It removes `942290` on
the route, and removes `942100` and `942151` only when `$filter` is present.
It does not remove `920100`.

The exceptions account for protocol syntax that can resemble SQL injection;
they are not an assertion that SQL injection is impossible. Authentication and
authorization are performed by Central's backend for cookie, Bearer, Basic,
field-key, and `st` requests.

## Aggregate anomaly rules (949110, 949111)

These rules remain enabled for `/v1/` and OData requests. They are not part of
the current exception policy.

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
# Exact OData GET route families; see the effective policy above.
SecRule REQUEST_METHOD "@streq GET" "id:1000201,phase:1,pass,nolog,chain"
  SecRule REQUEST_FILENAME "@rx ^/v1/(?:key/[^/]+/)?projects/[0-9]+/(?:forms/[^/]+(?:\.svc|/draft\.svc)|datasets/[^/]+\.svc)(?:/.*)?$" \
    "t:none,ctl:ruleRemoveById=942290"

SecRule REQUEST_METHOD "@streq GET" "id:1000202,phase:1,pass,nolog,chain"
  SecRule REQUEST_FILENAME "@rx ^/v1/(?:key/[^/]+/)?projects/[0-9]+/(?:forms/[^/]+(?:\.svc|/draft\.svc)|datasets/[^/]+\.svc)(?:/.*)?$" "chain"
    SecRule ARGS_NAMES "@streq $filter" \
      "t:none,ctl:ruleRemoveById=942100,ctl:ruleRemoveById=942151"
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
# No active exclusion. Aggregate anomaly rules remain enabled.
```

**Note:** This file is retained as historical documentation only.

---

## Historical recommendations (non-operative)

The following proposals are retained for history and are not part of the
effective policy above.

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

## Historical exclusion decision flow (superseded)

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

## Historical security assessment (superseded)

### Overall Risk: **LOW**

| Exclusion | Risk Level | Mitigation |
|-----------|------------|------------|
| 911100 (Methods) | LOW | Application validation |
| 942290 (SQLi) | LOW | Exact OData GET routes plus application parsing and parameterized queries |
| 949110, 949111 (Anomaly) | LOW | Auth + app validation |

**Why Safe:**
1. **Authentication Required:** All endpoints have auth
2. **Input Validation:** Application-level checks
3. **Parameterized Queries:** Reduce SQL injection risk after application parsing
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
