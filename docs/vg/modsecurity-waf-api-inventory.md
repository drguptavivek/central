# ModSecurity WAF API Inventory

> **Last Updated:** 2026-01-14
> **Version:** ODK Central v2025.4.1 (VG fork)
> **Purpose:** Comprehensive reference for ModSecurity WAF rule configuration

---

## Summary Tables

### Endpoints by Load Level

| Load | Count | Endpoints | WAF Priority |
|------|-------|-----------|--------------|
| **HIGH** | 15+ | Submissions, form sync, OData queries | Fast rules needed |
| **MEDIUM** | 40+ | Form management, entities, projects | Standard rules |
| **LOW** | 150+ | Admin, config, audits, roles | Standard rules |

### Endpoints by Command Injection Risk

| Risk | Count | Endpoints |
|------|-------|-----------|
| **NONE** | 195+ | Most endpoints (parameterized queries, safe parsing) |
| **LOW** | 5-10 | Login endpoints, file uploads |
| **MEDIUM** | 1 | `/v1/backup` (uses exec with config values) |

### Current CRS Rule Exclusions

| Rule | Description | Applied To | Reason |
|------|-------------|------------|--------|
| **911100** | Method enforcement | `/v1/` API | Allow PATCH/PUT/DELETE |
| **942290** | SQLi detection | OData `.svc/` | SQL-like syntax in $filter |
| **949110** | Blocking evaluation | `/v1/` API | Anomaly scoring adjustments |
| **949111** | Blocking evaluation | `/v1/` API | Anomaly scoring adjustments |

---

## Key Attributes

| Attribute | Values | Description |
|-----------|--------|-------------|
| **Route** | `/v1/path` | Full route pattern |
| **Methods** | GET/POST/PUT/PATCH/DELETE | HTTP methods allowed |
| **Auth** | Cookie/Bearer/Field Key/Basic/Anonymous | Authentication type |
| **Load** | HIGH/MEDIUM/LOW | Expected traffic frequency |
| **Payload** | SMALL (<1KB)/MEDIUM (1KB-1MB)/LARGE (>1MB) | Request size |
| **Risk** | NONE/LOW/MEDIUM/HIGH | Command injection risk |
| **CRS Exclusions** | Rule numbers | Specific CRS rules to disable |
| **Special** | Headers, file limits | Additional requirements |

---

## Detailed Endpoint Catalog

### 1. Authentication Endpoints

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `POST /v1/sessions` | POST | Cookie, Basic | HIGH | SMALL | LOW | - | Rate limit: 5/5min |
| `DELETE /v1/sessions/current` | DELETE | Cookie | LOW | SMALL | NONE | - | - |
| `DELETE /v1/sessions/:token` | DELETE | Cookie | LOW | SMALL | NONE | - | - |
| `GET /v1/sessions/restore` | GET | Cookie | LOW | SMALL | NONE | - | Session restore |
| `POST /v1/users/reset/initiate` | POST | Anonymous | LOW | SMALL | LOW | - | Password reset |
| `POST /v1/users/reset/verify` | POST | Anonymous | LOW | SMALL | LOW | - | Password reset |
| `POST /v1/projects/:id/app-users/login` | POST | Anonymous | HIGH | SMALL | LOW | - | Rate limit: 20/15min |
| `POST /v1/oidc/login` | POST | Anonymous | LOW | SMALL | NONE | - | SSO redirect |
| `GET /v1/oidc/callback` | GET | Anonymous | LOW | SMALL | NONE | - | SSO callback |

**WAF Notes:**
- Login endpoints have IP-based rate limiting
- `/v1/sessions` POST returns generic 401 (no user enumeration)
- OIDC endpoints are public (for SSO flow)

---

### 2. User Management

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/users` | GET | Cookie | LOW | SMALL | NONE | - | Admin only |
| `POST /v1/users` | POST | Cookie | LOW | SMALL | NONE | - | Create user |
| `GET /v1/users/current` | GET | Cookie | MEDIUM | SMALL | NONE | - | Self |
| `GET /v1/users/:id` | GET | Cookie | LOW | SMALL | NONE | - | User details |
| `PATCH /v1/users/:id` | PATCH | Cookie | LOW | SMALL | NONE | - | Update user |
| `DELETE /v1/users/:id` | DELETE | Cookie | LOW | SMALL | NONE | - | Delete user |
| `PUT /v1/users/:id/password` | PUT | Cookie | LOW | SMALL | LOW | - | Password change |

**WAF Notes:**
- Standard CRUD operations
- Password endpoints have validation (10+ chars, complexity)
- No special CRS exclusions needed

---

### 3. Project Management

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/projects` | GET | Cookie | MEDIUM | SMALL | NONE | - | List projects |
| `POST /v1/projects` | POST | Cookie | MEDIUM | SMALL | NONE | - | Create project |
| `GET /v1/projects/:id` | GET | Cookie | MEDIUM | SMALL | NONE | - | Project details |
| `PATCH /v1/projects/:id` | PATCH | Cookie | MEDIUM | SMALL | NONE | - | Update project |
| `DELETE /v1/projects/:id` | DELETE | Cookie | LOW | SMALL | NONE | - | Delete project |
| `POST /v1/projects/:id/key` | POST | Cookie | LOW | SMALL | NONE | - | Create key |
| `PUT /v1/projects/:id` | PUT | Cookie | MEDIUM | MEDIUM | NONE | - | Full update |

**WAF Notes:**
- PUT endpoint does full project update with nested forms/assignments
- Key creation generates field keys for external access

---

### 4. Form Management

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/projects/:id/forms` | GET | Mixed | HIGH | MEDIUM | NONE | - | Form list |
| `GET /v1/projects/:id/formList` | GET | Mixed | HIGH | SMALL | NONE | - | OpenROSA |
| `POST /v1/projects/:id/forms` | POST | Cookie | MEDIUM | LARGE | LOW | - | XLSForm upload |
| `GET /v1/.../forms/:id` | GET | Mixed | HIGH | MEDIUM | NONE | - | Form XML/XLS |
| `GET /v1/.../forms/:id/manifest` | GET | Mixed | HIGH | SMALL | NONE | - | OpenROSA |
| `PATCH /v1/.../forms/:id` | PATCH | Cookie | MEDIUM | SMALL | NONE | - | Update form |
| `DELETE /v1/.../forms/:id` | DELETE | Cookie | LOW | SMALL | NONE | - | Delete form |
| `POST /v1/.../forms/:id/draft` | POST | Cookie | MEDIUM | LARGE | LOW | - | Create draft |
| `POST /v1/.../draft/publish` | POST | Cookie | MEDIUM | SMALL | NONE | - | Publish draft |
| `DELETE /v1/.../forms/:id/draft` | DELETE | Cookie | MEDIUM | SMALL | NONE | - | Delete draft |

**WAF Notes:**
- **HIGH LOAD**: formList and forms list endpoints called frequently by mobile clients
- Form uploads accept XLSForm files (up to 100MB)
- OpenROSA endpoints require `X-OpenRosa-Version: 1.0` header
- Draft test endpoints (`/test/:key/...`) allow anonymous access with token

---

### 5. Submission Endpoints

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `POST /v1/projects/:id/submission` | POST | Bearer | **HIGH** | **LARGE** | LOW | - | OpenROSA multipart |
| `GET /v1/projects/:id/submission` | GET | Bearer | HIGH | SMALL | NONE | - | OpenROSA |
| `POST /v1/.../forms/:id/submissions` | POST | Bearer | **HIGH** | **LARGE** | LOW | - | REST JSON/XML |
| `PUT /v1/.../submissions/:id` | PUT | Bearer | **HIGH** | **LARGE** | LOW | - | Update submission |
| `GET /v1/.../submissions` | GET | Bearer | HIGH | MEDIUM | NONE | - | List submissions |
| `GET /v1/.../submissions/:id` | GET | Bearer | MEDIUM | MEDIUM | NONE | - | Submission details |
| `GET /v1/.../submissions/:id.xml` | GET | Bearer | MEDIUM | MEDIUM | NONE | - | XML export |
| `PATCH /v1/.../submissions/:id` | PATCH | Bearer | MEDIUM | SMALL | NONE | - | Partial update |
| `DELETE /v1/.../submissions/:id` | DELETE | Bearer | LOW | SMALL | NONE | - | Delete submission |
| `GET /v1/.../submissions/:id/edit` | GET | Bearer | MEDIUM | SMALL | NONE | - | Edit URL redirect |
| `POST /v1/.../submissions/:id/restore` | POST | Bearer | LOW | SMALL | NONE | - | Restore version |

**WAF Notes:**
- **HIGHEST LOAD ENDPOINTS**: submission POST/PUT called constantly by mobile clients
- **LARGE PAYLOAD**: multipart/form-data with attachments up to 100MB
- **Fast WAF rules recommended** for submission endpoints to avoid blocking legitimate traffic
- OpenROSA submission endpoint accepts multipart with `xml_submission_file` field
- Edit endpoint redirects to Enketo (302 response)

---

### 6. Submission Attachments

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/.../submissions/:id/attachments` | GET | Bearer | MEDIUM | SMALL | NONE | - | List attachments |
| `GET /v1/.../attachments/:name` | GET | Bearer | HIGH | MEDIUM | NONE | - | Download file |
| `POST /v1/.../attachments/:name` | POST | Bearer | HIGH | **LARGE** | LOW | - | Upload file |
| `DELETE /v1/.../attachments/:name` | DELETE | Bearer | LOW | SMALL | NONE | - | Delete attachment |

**WAF Notes:**
- **HIGH LOAD**: attachment downloads during form viewing
- **LARGE PAYLOAD**: file uploads up to 100MB
- Content-Type varies by file type

---

### 7. OpenROSA Endpoints

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/projects/:id/formList` | GET | Field Key | **HIGH** | SMALL | NONE | - | **X-OpenRosa-Version** |
| `GET /v1/.../forms/:id/manifest` | GET | Field Key | **HIGH** | SMALL | NONE | - | **X-OpenRosa-Version** |
| `POST /v1/projects/:id/submission` | POST | Field Key | **HIGH** | **LARGE** | LOW | - | **multipart/form-data** |
| `GET /v1/test/:key/.../draft/formList` | GET | Anonymous | MEDIUM | SMALL | NONE | - | Draft testing |
| `GET /v1/test/:key/.../draft/manifest` | GET | Anonymous | MEDIUM | SMALL | NONE | - | Draft testing |
| `GET /v1/test/:key/.../draft.xml` | GET | Anonymous | MEDIUM | MEDIUM | NONE | - | Draft XML |
| `POST /v1/test/:key/.../draft/submission` | POST | Anonymous | MEDIUM | **LARGE** | LOW | - | Draft testing |

**WAF Notes:**
- **CRITICAL FOR WAF**: These are the most frequently called endpoints (mobile sync)
- **Headers Required**: `X-OpenRosa-Version: 1.0` (WAF should validate this header)
- **Headers Set**: `X-OpenRosa-Accept-Content-Length: 104857600`
- **Content-Type**: `multipart/form-data` for submissions
- **File size**: Up to 100MB accepted
- **Test endpoints**: Anonymous access with draft token in URL

**CRS Exclusions Needed:**
- Consider allowing large payloads for submission endpoints
- May need to relax body size limits for multipart submissions

---

### 8. OData Endpoints

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/.../forms/:id.svc` | GET | Field Key | **HIGH** | SMALL | NONE | **942290** | Metadata |
| `GET /v1/.../forms/:id.svc/\$metadata` | GET | Field Key | HIGH | SMALL | NONE | **942290** | OData metadata |
| `GET /v1/.../forms/:id.svc/Submissions` | GET | Field Key | **HIGH** | MEDIUM | NONE | **942290** | OData feed |
| `GET /v1/.../forms/:id.svc/Submissions(:uuid)` | GET | Field Key | HIGH | MEDIUM | NONE | **942290** | Single entity |
| `GET /v1/.../datasets/:name.svc` | GET | Field Key | MEDIUM | SMALL | NONE | **942290** | Entity metadata |
| `GET /v1/.../datasets/:name.svc/Entities` | GET | Field Key | MEDIUM | MEDIUM | NONE | **942290** | Entity feed |

**WAF Notes:**
- **HIGH LOAD**: OData queries called frequently for data sync
- **CRS 942290 EXCLUDED**: SQLi detection disabled due to OData syntax
- **OData syntax**: `$filter`, `$select`, `$orderby`, `$top`, `$skip`
- **SQL-like patterns**: `$filter=field eq 'value'` triggers SQLi rules
- **Query strings**: Can be very long (complex filters)

**CRS Exclusions (Current):**
```nginx
# In files/nginx/odk.conf.template and crs_custom/20-odk-odata-exclusions.conf
SecRuleRemoveById 942290  # SQLi detection for OData
```

---

### 9. Entity & Dataset Endpoints

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/.../datasets` | GET | Cookie | MEDIUM | SMALL | NONE | - | List datasets |
| `POST /v1/.../datasets` | POST | Cookie | MEDIUM | SMALL | NONE | - | Create dataset |
| `GET /v1/.../datasets/:name` | GET | Cookie | MEDIUM | SMALL | NONE | - | Dataset details |
| `PATCH /v1/.../datasets/:name` | PATCH | Cookie | MEDIUM | SMALL | NONE | - | Update dataset |
| `GET /v1/.../datasets/:name/entities` | GET | Bearer | MEDIUM | MEDIUM | NONE | - | List entities |
| `POST /v1/.../datasets/:name/entities` | POST | Bearer | MEDIUM | **LARGE** | LOW | - | Create entity |
| `GET /v1/.../entities/:uuid` | GET | Bearer | MEDIUM | MEDIUM | NONE | - | Entity details |
| `PATCH /v1/.../entities/:uuid` | PATCH | Bearer | MEDIUM | SMALL | NONE | - | Update entity |
| `DELETE /v1/.../entities/:uuid` | DELETE | Bearer | LOW | SMALL | NONE | - | Delete entity |
| `POST /v1/.../entities/bulk-delete` | POST | Bearer | LOW | MEDIUM | NONE | - | Bulk delete |
| `GET /v1/.../entities.geojson` | GET | Bearer | MEDIUM | **LARGE** | NONE | - | GeoJSON export |

**WAF Notes:**
- Entity creation accepts JSON arrays (bulk: up to 100MB)
- GeoJSON exports can be large (all entities with coordinates)
- OData entity endpoints use same `.svc` pattern

---

### 10. App User Management (VG)

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/.../app-users` | GET | Cookie | MEDIUM | SMALL | NONE | - | List app users |
| `POST /v1/.../app-users` | POST | Cookie | MEDIUM | SMALL | NONE | - | Create app user |
| `GET /v1/.../app-users/:id` | GET | Cookie | LOW | SMALL | NONE | - | App user details |
| `PATCH /v1/.../app-users/:id` | PATCH | Cookie | LOW | SMALL | NONE | - | Update app user |
| `DELETE /v1/.../app-users/:id` | DELETE | Cookie | LOW | SMALL | NONE | - | Delete app user |
| `POST /v1/.../app-users/login` | POST | Anonymous | **HIGH** | SMALL | LOW | - | **IP rate limit** |
| `POST /v1/.../app-users/:id/password/change` | POST | Bearer | LOW | SMALL | LOW | - | Self password |
| `POST /v1/.../app-users/:id/password/reset` | POST | Cookie | LOW | SMALL | LOW | - | Admin reset |
| `POST /v1/.../app-users/:id/revoke` | POST | Bearer | LOW | SMALL | NONE | - | Self revoke |
| `POST /v1/.../app-users/:id/revoke-admin` | POST | Cookie | LOW | SMALL | NONE | - | Admin revoke |
| `POST /v1/.../app-users/:id/active` | POST | Cookie | LOW | SMALL | NONE | - | Activate/deactivate |
| `GET /v1/.../app-users/:id/sessions` | GET | Cookie | LOW | SMALL | NONE | - | List sessions |
| `GET /v1/.../app-users/sessions` | GET | Cookie | LOW | SMALL | NONE | - | List all sessions |
| `POST /v1/.../sessions/:id/revoke` | POST | Cookie | LOW | SMALL | NONE | - | Revoke session |

**WAF Notes:**
- **HIGH LOAD**: Login endpoint with IP-based rate limiting (20/15min → 30min lock)
- Password policy: 10+ chars, upper/lower/digit/special
- Lockout tracked in `vg_app_user_lockouts`

---

### 11. System Settings (VG)

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/system/settings` | GET | Cookie | LOW | SMALL | NONE | - | Admin only |
| `PUT /v1/system/settings` | PUT | Cookie | LOW | SMALL | LOW | - | Admin only |
| `GET /v1/.../app-users/settings` | GET | Cookie | LOW | SMALL | NONE | - | Project settings |
| `PUT /v1/.../app-users/settings` | PUT | Cookie | LOW | SMALL | NONE | - | Project override |
| `POST /v1/system/app-users/lockouts/clear` | POST | Cookie | LOW | SMALL | NONE | - | Clear lockouts |

**WAF Notes:**
- Settings include: session TTL, session cap, IP rate limit thresholds
- PUT allows partial updates (only specified fields)

---

### 12. Telemetry (VG)

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `POST /v1/.../app-users/telemetry` | POST | Bearer | MEDIUM | MEDIUM | LOW | - | Batch events |
| `GET /v1/system/app-users/telemetry` | GET | Cookie | LOW | SMALL | NONE | - | Admin view |

**WAF Notes:**
- Telemetry accepts batch JSON (array of events)
- Includes location tracking and session data

---

### 13. Enketo Status (VG)

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/system/enketo-status` | GET | Cookie | LOW | MEDIUM | NONE | - | Admin only |
| `POST /v1/system/enketo-status/regenerate` | POST | Cookie | LOW | SMALL | NONE | - | Admin only |

**WAF Notes:**
- Status endpoint returns form Enketo integration status
- Regenerate creates new Enketo IDs for specified forms

---

### 14. Roles & Assignments

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/roles` | GET | Cookie | LOW | SMALL | NONE | - | List roles |
| `GET /v1/roles/:id` | GET | Cookie | LOW | SMALL | NONE | - | Role details |
| `GET /v1/assignments` | GET | Cookie | LOW | SMALL | NONE | - | List assignments |
| `POST /v1/assignments/:roleId/:actorId` | POST | Cookie | LOW | SMALL | NONE | - | Create assignment |
| `DELETE /v1/assignments/:roleId/:actorId` | DELETE | Cookie | LOW | SMALL | NONE | - | Delete assignment |
| `GET /v1/projects/:id/assignments` | GET | Cookie | MEDIUM | SMALL | NONE | - | Project assignments |

---

### 15. Audit & Analytics

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/audits` | GET | Cookie | LOW | MEDIUM | NONE | - | Audit log |
| `GET /v1/analytics/preview` | GET | Cookie | LOW | SMALL | NONE | - | Analytics data |

---

### 16. Backup (Command Injection Risk)

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `POST /v1/backup` | POST | Cookie | **LOW** | **LARGE** | **MEDIUM** | - | **exec() call** |

**WAF Notes:**
- **MEDIUM RISK**: Uses `exec()` with pg_dump command
- Config values interpolated into command string
- **Recommendation**: Strict rate limiting, admin-only access
- File: `server/lib/task/db.js:27, 58`

---

### 17. Config Endpoints

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/config/:key` | GET | Cookie | LOW | SMALL | NONE | - | Get config |
| `POST /v1/config/:key` | POST | Cookie | LOW | SMALL | NONE | - | Set config |
| `DELETE /v1/config/:key` | DELETE | Cookie | LOW | SMALL | NONE | - | Clear config |

---

### 18. Comments

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/.../submissions/:id/comments` | GET | Bearer | LOW | SMALL | NONE | - | List comments |
| `POST /v1/.../submissions/:id/comments` | POST | Bearer | LOW | SMALL | LOW | - | Add comment |

**WAF Notes:**
- Comment body is user input (XSS risk handled at application level)

---

### 19. Public Links

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `GET /v1/.../forms/:id/public-links` | GET | Cookie | LOW | SMALL | NONE | - | List links |
| `POST /v1/.../forms/:id/public-links` | POST | Cookie | LOW | SMALL | NONE | - | Create link |
| `DELETE /v1/.../public-links/:id` | DELETE | Cookie | LOW | SMALL | NONE | - | Delete link |

---

### 20. User Preferences

| Route | Methods | Auth | Load | Payload | Risk | CRS | Special |
|-------|---------|------|------|---------|------|-----|---------|
| `PUT /v1/user-preferences/project/:id/:prop` | PUT | Cookie | LOW | SMALL | NONE | - | Set preference |
| `DELETE /v1/user-preferences/project/:id/:prop` | DELETE | Cookie | LOW | SMALL | NONE | - | Clear preference |

---

## Authentication Patterns

| Type | Description | Endpoints | WAF Considerations |
|------|-------------|-----------|-------------------|
| **Cookie** | Web session cookie (`__Host-session`) | Most web UI | CSRF validation required |
| **Bearer** | Short-lived app user tokens | App endpoints | Token in `Authorization` header |
| **Field Key** | `/key/{token}` or `?st={token}` | OpenROSA/OData | No 401, returns 403 |
| **Basic** | HTTP Basic auth | Legacy login | HTTPS only |
| **Anonymous** | No auth required | Login, OIDC, test | Public endpoints |

---

## WAF Configuration Recommendations

### 1. High-Load Endpoints (Fast Rules Required)

These endpoints need optimized WAF rules to avoid performance impact:

```
POST /v1/projects/:projectId/submission        (OpenROSA submission)
POST /v1/.../forms/:xmlFormId/submissions     (REST submission)
GET  /v1/projects/:projectId/formList         (OpenROSA form list)
GET  /v1/.../forms/:xmlFormId.svc/*           (OData queries)
POST /v1/projects/:projectId/app-users/login   (App user login)
```

**Recommendations:**
- Use SecRuleRemoveById for known-safe patterns
- Consider SecAction with "pass,nolog" for high-volume traffic
- Monitor for false positives

### 2. Command Injection Protection

**Medium Risk:**
```
POST /v1/backup    # Uses exec() with config values
```

**Recommendations:**
- Strict rate limiting (admin only)
- Monitor for command injection patterns
- Consider additional authentication

### 3. Current CRS Exclusions

**Already configured:**
```nginx
# Location: files/nginx/odk.conf.template, crs_custom/
location ~ ^/v\d {
    # Disable CRS blocking rules for Central API
    modsecurity_rules 'SecRuleRemoveById 911100 949110 949111';
}

# Location: crs_custom/20-odk-odata-exclusions.conf
# OData SQL-like syntax
SecRule REQUEST_URI "@endsWith .svc" \
    "id:1000,phase:2,pass,nolog,ctl:ruleRemoveById=942290"
```

### 4. Recommended Additional Exclusions

**Consider adding:**
```nginx
# Large multipart submissions
SecRule REQUEST_METHOD "@streq POST" \
    "SecRule REQUEST_URI "@endsWith /submission" \
    "id:1001,phase:1,pass,nolog,ctl:requestBodyLimit=104857600"

# OpenROSA header validation
SecRule &REQUEST_HEADERS:X-OpenRosa-Version "@eq 0" \
    "id:1002,phase:1,deny,status=400,msg='Missing OpenROSA header'"
```

---

## Rate Limiting Summary

| Endpoint | Type | Limit | Lockout |
|----------|------|-------|---------|
| `/v1/sessions` (POST) | Web login | 5/5min | 10 min |
| `/v1/.../app-users/login` (POST) | App login | 20/15min | 30 min |
| All other endpoints | None | None | None |

**Recommendation:** Consider adding rate limiting for:
- Submission endpoints (prevent abuse)
- OData query endpoints (prevent scraping)
- Form upload endpoints (prevent storage abuse)

---

## File Upload Endpoints

| Endpoint | Max Size | Content-Type | Auth |
|----------|----------|--------------|------|
| `POST /v1/.../submission` | 100MB | multipart/form-data | Bearer |
| `POST /v1/.../attachments/:name` | 100MB | multipart/form-data | Bearer |
| `POST /v1/projects/:id/forms` | 100MB | application/octet-stream | Cookie |
| `POST /v1/.../datasets/:name/entities` | 100MB | application/json | Bearer |

**WAF Notes:**
- All file uploads require authentication
- Content-Type validation handled at application level
- Consider SecRuleUpdateActionById for file size limits

---

## Related Documentation

- **VG Route Documentation:** `docs/vg/vg-server/routes/`
- **Modsecurity Config:** `docs/vg/vg_modsecurity.md`
- **CRS Exclusions:** `crs_custom/*.conf`
- **Nginx Config:** `files/nginx/odk.conf.template`

---

## Verification Checklist

- [ ] All 200+ endpoints documented
- [ ] Each endpoint has HTTP methods, auth type, load, risk
- [ ] CRS exclusions documented with specific rule numbers
- [ ] Command injection risks identified
- [ ] High-load endpoints marked for optimization
- [ ] File upload endpoints documented with size limits

---

*Generated from comprehensive exploration of ODK Central v2025.4.1 server codebase*
