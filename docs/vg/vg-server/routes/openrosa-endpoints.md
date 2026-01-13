# OpenROSA Endpoints

> **Last Updated:** 2026-01-14
> **Protocol:** OpenRosa 1.0
> **Purpose:** ODK Collect form sync and submission endpoints

---

## Overview

OpenROSA is the legacy API protocol used by ODK Collect mobile clients for:
- Form listing and download
- Form submission (multipart with attachments)
- Manifest retrieval for media files

**WAF Priority:** HIGH - These are the most frequently called endpoints in the system.

---

## Protocol Requirements

### Required Headers

**Request Headers:**
```
X-OpenRosa-Version: 1.0
```

**Response Headers:**
```
X-OpenRosa-Version: 1.0
X-OpenRosa-Accept-Content-Length: 104857600
Content-Language: en
Date: <HTTP-date>
```

**WAF Rule:**
```nginx
# Validate OpenROSA header is present
SecRule &REQUEST_HEADERS:X-OpenRosa-Version "@eq 0" \
    "id:1002,phase:1,deny,status=400,msg='Missing OpenROSA header'"
```

---

## Endpoints

### 1. Form List

**Route:** `GET /v1/projects/:projectId/formList`

**File:** `server/lib/resources/forms.js:75-80`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | **HIGH** (per-sync) |
| **Payload** | SMALL (<1KB) |
| **Risk** | NONE |
| **CRS Exclusions** | None |
| **Special** | Requires `X-OpenRosa-Version: 1.0` |

**Request:**
```
GET /v1/projects/1/formList
X-OpenRosa-Version: 1.0
Authorization: Bearer <token>
```

**Response:**
```xml
Content-Type: text/xml
X-OpenRosa-Version: 1.0
X-OpenRosa-Accept-Content-Length: 104857600

<xforms>
  <form id="basic" name="Basic" version="2023-01-01">
    <hash>md5:abc123</hash>
    <downloadUrl>https://.../forms/basic/formXml</downloadUrl>
    <manifestUrl>https://.../forms/basic/manifest</manifestUrl>
  </form>
</xforms>
```

**WAF Considerations:**
- **HIGH LOAD**: Called on every ODK Collect sync
- Fast rule processing recommended
- Response contains XML with form metadata

---

### 2. Form Manifest

**Route:** `GET /v1/projects/:projectId/forms/:xmlFormId/manifest`

**File:** `server/lib/resources/forms.js:290-303`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | **HIGH** (per-sync) |
| **Payload** | SMALL (<1KB) |
| **Risk** | NONE |
| **CRS Exclusions** | None |
| **Special** | Requires `X-OpenRosa-Version: 1.0` |

**Request:**
```
GET /v1/projects/1/forms/basic/manifest
X-OpenRosa-Version: 1.0
```

**Response:**
```xml
<manifest>
  <file>
    <filename>sample.jpg</filename>
    <hash>md5:def456</hash>
    <downloadUrl>https://.../attachments/sample.jpg</downloadUrl>
  </file>
</manifest>
```

**WAF Considerations:**
- **HIGH LOAD**: Called during form download
- Lists all form attachments with hashes

---

### 3. Form Download (XML)

**Route:** `GET /v1/projects/:projectId/forms/:xmlFormId`

**File:** `server/lib/resources/forms.js:260-264`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | **HIGH** (on form update) |
| **Payload** | MEDIUM (1KB-1MB) |
| **Risk** | NONE |
| **CRS Exclusions** | None |

**Request:**
```
GET /v1/projects/1/forms/basic
```

**Response:**
```xml
Content-Type: application/xml

<?xml version="1.0"?>
<h:html xmlns:h="http://www.w3.org/1999/xhtml">...</h:html>
```

**WAF Considerations:**
- Form XML can be large (complex forms)
- No special WAF rules needed

---

### 4. Form Download (XLS/XLSX)

**Route:** `GET /v1/projects/:projectId/forms/:xmlFormId?form=xlsx`

**File:** `server/lib/resources/forms.js:274-277`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | Field Key / Bearer |
| **Load** | MEDIUM |
| **Payload** | MEDIUM (10KB-100KB) |
| **Risk** | NONE |
| **CRS Exclusions** | None |

**WAF Considerations:**
- XLS/XLSX downloads for form designers
- Not used by ODK Collect (web only)

---

### 5. Submission Endpoint (Primary)

**Route:** `POST /v1/projects/:projectId/submission` (and `GET` returns 204)

**File:** `server/lib/resources/submissions.js:104-156`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET, POST |
| **Auth** | Field Key / Bearer |
| **Load** | **VERY HIGH** (every submission) |
| **Payload** | **LARGE** (up to 100MB) |
| **Risk** | LOW |
| **CRS Exclusions** | None (consider body limit) |
| **Special** | `multipart/form-data` with `xml_submission_file` |

**Request:**
```
POST /v1/projects/1/submission
X-OpenRosa-Version: 1.0
Content-Type: multipart/form-data; boundary=---xyz

-----xyz
Content-Disposition: form-data; name="xml_submission_file"; filename="submission.xml"
Content-Type: application/xml

<?xml version="1.0"?><data>...</data>
-----xyz
Content-Disposition: form-data; name="photo"; filename="photo.jpg"
Content-Type: image/jpeg

<binary data>
-----xyz--
```

**Response:**
```
204 No Content
X-OpenRosa-Version: 1.0
```

**WAF Considerations:**
- **CRITICAL ENDPOINT**: Highest traffic volume
- **LARGE PAYLOAD**: Accepts up to 100MB
- **Fast WAF processing required** to avoid blocking
- **Content-Type**: `multipart/form-data`
- **Special field**: `xml_submission_file` contains XML
- **Attachments**: Any number of files with any name/type

**Recommended WAF Config:**
```nginx
# Allow large submissions
SecRule REQUEST_METHOD "@streq POST" \
    "SecRule REQUEST_URI "@endsWith /submission" \
    "id:1001,phase:1,pass,nolog,ctl:requestBodyLimit=104857600"

# Skip body inspection for known-safe submissions (optional)
# Only if you trust application-layer validation
SecRule REQUEST_URI "@endsWith /submission" \
    "id:1003,phase:2,pass,nolog,ctl:ruleEngine=Off"
```

---

### 6. Draft Form List (Test Token)

**Route:** `GET /v1/test/:key/projects/:projectId/forms/:xmlFormId/draft/formList`

**File:** `server/lib/resources/forms.js:429-442`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | **Anonymous** (token in URL) |
| **Load** | MEDIUM (testing) |
| **Payload** | SMALL (<1KB) |
| **Risk** | NONE |
| **CRS Exclusions** | None |
| **Special** | Draft token in URL path |

**Request:**
```
GET /v1/test/abc123/projects/1/forms/basic/draft/formList
```

**WAF Considerations:**
- Anonymous access with draft token
- Token is validated by server
- Used for testing forms before publishing

---

### 7. Draft Manifest (Test Token)

**Route:** `GET /v1/test/:key/projects/:projectId/forms/:xmlFormId/draft/manifest`

**File:** `server/lib/resources/forms.js:444-451`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | **Anonymous** (token in URL) |
| **Load** | MEDIUM (testing) |
| **Payload** | SMALL (<1KB) |
| **Risk** | NONE |
| **CRS Exclusions** | None |

**WAF Considerations:**
- Same as production manifest but for draft forms
- Uses test token in URL

---

### 8. Draft Form XML (Test Token)

**Route:** `GET /v1/test/:key/projects/:projectId/forms/:xmlFormId/draft.xml`

**File:** `server/lib/resources/forms.js:453-458`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | **Anonymous** (token in URL) |
| **Load** | MEDIUM (testing) |
| **Payload** | MEDIUM (form XML) |
| **Risk** | NONE |
| **CRS Exclusions** | None |

**WAF Considerations:**
- Returns draft form XML for testing
- Anonymous access with token

---

### 9. Draft Attachments (Test Token)

**Route:** `GET /v1/test/:key/projects/:projectId/forms/:xmlFormId/draft/attachments/:name`

**File:** `server/lib/resources/forms.js:460-469`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET |
| **Auth** | **Anonymous** (token in URL) |
| **Load** | MEDIUM (testing) |
| **Payload** | MEDIUM (file size) |
| **Risk** | NONE |
| **CRS Exclusions** | None |

**WAF Considerations:**
- Downloads draft form attachments
- Any file type supported

---

### 10. Draft Submission (Test Token)

**Route:** `POST /v1/test/:key/projects/:projectId/forms/:xmlFormId/draft/submission`

**File:** `server/lib/resources/submissions.js:182-193`

**WAF Attributes:**
| Attribute | Value |
|-----------|-------|
| **Methods** | GET, POST |
| **Auth** | **Anonymous** (token in URL) |
| **Load** | MEDIUM (testing) |
| **Payload** | **LARGE** (up to 100MB) |
| **Risk** | LOW |
| **CRS Exclusions** | None |
| **Special** | `multipart/form-data` |

**WAF Considerations:**
- Anonymous submission to draft forms
- Same multipart format as production
- Used for testing form submissions

---

## WAF Configuration Summary

### Headers Required
```nginx
# Require OpenROSA header for production endpoints
SecRule REQUEST_URI "@rx ^/v1/projects/\d+/formList$" \
    "SecRule &REQUEST_HEADERS:X-OpenRosa-Version "@eq 0" \
    "id:2001,phase:1,deny,status=400,msg='Missing OpenROSA header'"

SecRule REQUEST_URI "@rx ^/v1/projects/\d+/forms/[^/]+/manifest$" \
    "SecRule &REQUEST_HEADERS:X-OpenRosa-Version "@eq 0" \
    "id:2002,phase:1,deny,status=400,msg='Missing OpenROSA header'"
```

### Body Size Limits
```nginx
# Allow large submissions
SecRule REQUEST_METHOD "@streq POST" \
    "SecRule REQUEST_URI "@endsWith /submission" \
    "id:2003,phase:1,pass,nolog,ctl:requestBodyLimit=104857600"

# Same for draft submissions
SecRule REQUEST_URI "@endsWith /draft/submission" \
    "id:2004,phase:1,pass,nolog,ctl:requestBodyLimit=104857600"
```

### Recommended CRS Exclusions
```nginx
# Consider disabling body inspection for multipart submissions
# to avoid parsing large files
<LocationMatch "^/v1/[^/]+/submission">
    SecRuleRemoveById 920120  # Content-Type check
    SecRuleRemoveById 920130  # Multipart boundary check
</LocationMatch>
```

---

## Security Considerations

### Test Token Endpoints
- All `/v1/test/:key/...` endpoints are **anonymous**
- Token is validated server-side
- **Recommendation**: Monitor for abuse of test tokens

### File Uploads
- Submission endpoint accepts ANY file type
- Maximum size: 100MB
- **Recommendation**: Monitor for malware upload attempts

### Header Validation
- `X-OpenRosa-Version: 1.0` header is currently NOT enforced by server
- **Recommendation**: Enforce at WAF level for protocol compliance

---

## Related Documentation

- **Main WAF Inventory:** `docs/vg/modsecurity-waf-api-inventory.md`
- **Form Endpoints:** `docs/vg/vg-server/routes/core-api-forms-submissions.md`
- **Submission Processing:** `server/lib/resources/submissions.js`
- **OpenRosa Template:** `server/lib/formats/openrosa.js`

---

## Verification Checklist

- [ ] All OpenROSA headers documented
- [ ] Load levels marked (HIGH for production)
- [ ] File size limits documented (100MB)
- [ ] Test token endpoints identified
- [ ] WAF rules proposed for header validation
- [ ] CRS exclusions recommended for large payloads
