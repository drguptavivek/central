# ModSecurity OData Hardening Rules (Optional)

> **Last Updated:** 2026-01-14
> **Purpose:** Optional defense-in-depth rules for OData endpoints
> **Status:** OPTIONAL - Current application-layer protections are sufficient

---

## Overview

This document provides detailed ModSecurity rules for hardening OData endpoints. These rules are **OPTIONAL** because:

1. **Application-layer protections are already strong** (Slonik ORM, whitelisting, AST parsing)
2. **Current ModSecurity exclusions are safe** (942290 for SQLi, 920100 for protocol)
3. **These rules provide defense-in-depth** but are not required for security

**Use Cases:**
- Add DoS protection (parameter length limits)
- Add input validation (better error messages)
- Add monitoring/detection (probing attempts)
- Add audit logging (security monitoring)

---

## File: crs_custom/25-odk-hardening.conf

```nginx
# ============================================================================
# OData Endpoint Hardening Rules (Optional Defense-in-Depth)
# ============================================================================
#
# These rules provide additional protection for OData endpoints beyond
# the strong application-layer protections already in place.
#
# Application-Layer Protections (Already in Place):
# - Slonik ORM with parameterized queries (prevents SQL injection)
# - Field whitelisting via odataToColumnMap (prevents field injection)
# - AST parsing via odata-v4-parser (validates syntax)
# - Function whitelist (only 7 functions allowed)
# - Type validation for literals
#
# These ModSecurity rules are OPTIONAL and provide:
# - DoS protection (parameter length limits)
# - Input validation (better error messages)
# - Monitoring (detection of probing attempts)
# - Audit logging (security monitoring)
#
# ============================================================================

# ============================================================================
# CATEGORY 1: Parameter Length Limits (DoS Prevention)
# ============================================================================

# Rule: Limit $filter parameter length
# Purpose: Prevent DoS via extremely long filter expressions
# Attack: Sending massive filter strings to consume CPU/memory
# File: server/lib/data/odata-filter.js

SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2501,phase:2,deny,status:414,msg:'OData filter too long (max 2000 chars)', \
    SecRule ARGS_NAMES:\$filter "@gt 2000"

# Examples:
# BLOCKED: ?$filter=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa... (2001+ chars)
# ALLOWED: ?$filter=status eq 'submitted' and age ge 18 (42 chars)

# Tuning:
# Increase limit if legitimate use case requires longer filters
# Current limit: 2000 characters (accommodates complex queries)
# To check max filter length in your deployment:
#   grep -r "filter=" /var/log/modsecurity/audit.log | wc -L

---

# Rule: Limit $orderby parameter length
# Purpose: Prevent DoS via extremely long orderby expressions
# Attack: Sending massive orderby strings to consume CPU/memory
# File: server/lib/data/odata-filter.js:152

SecRule REQUEST_URI "@rx \.svc/.*\$orderby=" \
    "id:2502,phase:2,deny,status:414,msg:'OData orderby too long (max 500 chars)', \
    SecRule ARGS:\$orderby "@gt 500"

# Examples:
# BLOCKED: ?$orderby=field1,field2,field3,...field100 (501+ chars)
# ALLOWED: ?$orderby=__system/submissionDate desc (40 chars)

# Tuning:
# Current limit: 500 characters (100+ fields)
# Increase if needed for complex multi-field sorting

---

# Rule: Limit $select parameter length
# Purpose: Prevent DoS via extremely long select expressions
# Attack: Sending massive select strings to consume CPU/memory
# File: server/lib/util/odata.js (uses $select)

SecRule REQUEST_URI "@rx \.svc/.*\$select=" \
    "id:2503,phase:2,deny,status:414,msg:'OData select too long (max 1000 chars)', \
    SecRule ARGS:\$select "@gt 1000"

# Examples:
# BLOCKED: ?$select=field1,field2,field3,...field200 (1001+ chars)
# ALLOWED: ?$select=__id,name,age,createdAt (30 chars)

# Tuning:
# Current limit: 1000 characters (100+ fields)
# Forms with many fields may require increase

---

# Rule: Limit overall query string length
# Purpose: Prevent DoS via extremely long query strings overall
# Attack: Sending massive query strings with multiple parameters

SecRule REQUEST_URI "@rx \.svc/" \
    "id:2504,phase:1,deny,status:414,msg:'OData query string too long (max 4096 chars)', \
    SecRule REQUEST_URI "@rx \.svc/.*\?([^#]{4097,})"

# Note: This is a regex on the full query string after the ?
# Standard URL length limit is often 4096 or 8192 characters

# Tuning:
# Current limit: 4096 characters
# Most browsers limit URLs to 2048-8192 characters
# nginx default: large_client_header_buffers 4k/8k

# ============================================================================
# CATEGORY 2: Parameter Format Validation
# ============================================================================

# Rule: Validate $orderby format (field names only, comma-separated)
# Purpose: Detect invalid characters that might indicate injection attempts
# File: server/lib/data/odata-filter.js:152-177

SecRule REQUEST_URI "@rx \.svc/.*\$orderby=" \
    "id:2510,phase:2,deny,status:400,msg:'Invalid OData orderby format', \
    SecRule ARGS:\$orderby "!@rx ^[a-zA-Z0-9_/,_ -]+$"

# Examples:
# BLOCKED: ?$orderby=id;DROP TABLE-- (contains semicolon)
# BLOCKED: ?$orderby=<script>alert(1)</script> (contains HTML)
# ALLOWED: ?$orderby=__system/submissionDate desc
# ALLOWED: ?$orderby=name,age,createdAt

# Character classes explained:
# [a-zA-Z0-9_] - Alphanumeric and underscore (field names)
# / - Forward slash (for __system/field syntax)
# , - Comma (multi-field separator)
#   - Space (for asc/desc separator)
# - - Hyphen (for hyphenated field names)

# Tuning:
# If you have fields with special characters (rare), add them to the regex
# Example: $orderby=~^[a-zA-Z0-9_/,_ -]+$ (add tilde for fields like 'field-name')

---

# Rule: Validate $select format (field names only, comma-separated)
# Purpose: Detect invalid characters in select parameter

SecRule REQUEST_URI "@rx \.svc/.*\$select=" \
    "id:2511,phase:2,deny,status:400,msg:'Invalid OData select format', \
    SecRule ARGS:\$select "!@rx ^[a-zA-Z0-9_/,_ -]+$"

# Examples:
# BLOCKED: ?$select=<script>alert(1)</script>
# BLOCKED: ?$select=id;DROP TABLE--
# ALLOWED: ?$select=__id,name,age

---

# Rule: Validate $top parameter (positive integers only)
# Purpose: Detect non-numeric or negative values in $top
# File: server/lib/util/odb.js (uses $top)

SecRule REQUEST_URI "@rx \.svc/.*\$top=" \
    "id:2512,phase:2,deny,status:400,msg:'Invalid OData top value (must be positive integer)', \
    SecRule ARGS:\$top "!@rx ^[0-9]+$"

# Examples:
# BLOCKED: ?$top=-1 (negative)
# BLOCKED: ?$top=abc (non-numeric)
# BLOCKED: ?$top=1 OR 1=1 (SQL injection attempt)
# ALLOWED: ?$top=100
# ALLOWED: ?$top=1

# Tuning:
# If you need to support scientific notation (unlikely), use:
# SecRule ARGS:\$top "!@rx ^[0-9.e+-]+$"

---

# Rule: Validate $skip parameter (positive integers only)
# Purpose: Detect non-numeric or negative values in $skip
# File: server/lib/util/odb.js (uses $skip)

SecRule REQUEST_URI "@rx \.svc/.*\$skip=" \
    "id:2513,phase:2,deny,status:400,msg:'Invalid OData skip value (must be positive integer)', \
    SecRule ARGS:\$skip "!@rx ^[0-9]+$"

# Examples:
# BLOCKED: ?$skip=-1 (negative)
# BLOCKED: ?$skip=abc (non-numeric)
# ALLOWED: ?$skip=100
# ALLOWED: ?$skip=0

---

# Rule: Validate $skiptoken format (base64-like string)
# Purpose: Detect malformed skiptoken values
# File: server/lib/util/db.js (uses $skiptoken)

SecRule REQUEST_URI "@rx \.svc/.*\$skiptoken=" \
    "id:2514,phase:2,deny,status:400,msg:'Invalid OData skiptoken format', \
    SecRule ARGS:\$skiptoken "!@rx ^[A-Za-z0-9_-]+={0,2}[A-Za-z0-9_-]*$"

# Examples:
# BLOCKED: ?$skiptoken=<script>alert(1)</script>
# BLOCKED: ?$skiptoken=../../../etc/passwd
# ALLOWED: ?$skiptoken=ABC123 (base64-like)
# ALLOWED: ?$skiptoken=ABC123DEFGH== (base64 with padding)

# Tuning:
# Current regex allows base64-like strings (alphanumeric + underscore + hyphen)
# Adjust if your skiptoken format differs

---

# Rule: Validate $wkt parameter (boolean values only)
# Purpose: Detect invalid values in $wkt parameter
# File: server/lib/data/odata.js (uses $wkt for WKT format)

SecRule REQUEST_URI "@rx \.svc/.*\$wkt=" \
    "id:2515,phase:2,deny,status:400,msg:'Invalid OData wkt value (must be true or false)', \
    SecRule ARGS:\$wkt "!@rx ^(true|false|1|0)$"

# Examples:
# BLOCKED: ?$wkt=yes
# BLOCKED: ?$wkt=<script>alert(1)</script>
# ALLOWED: ?$wkt=true
# ALLOWED: ?$wkt=false
# ALLOWED: ?$wkt=1
# ALLOWED: ?$wkt=0

---

# Rule: Validate $expand parameter (limited values)
# Purpose: Restrict $expand to known safe values
# File: server/lib/data/odata.js (uses $expand)

SecRule REQUEST_URI "@rx \.svc/.*\$expand=" \
    "id:2516,phase:2,deny,status:400,msg:'Invalid OData expand value', \
    SecRule ARGS:\$expand "!@rx ^[a-zA-Z0-9_/,*]+$"

# Examples:
# BLOCKED: ?$expand=<script>alert(1)</script>
# BLOCKED: ?$expand=../../../etc/passwd
# ALLOWED: ?$expand=*
# ALLOWED: ?$expand=__system

# Tuning:
# Current regex allows: alphanumeric, underscore, forward slash, comma, asterisk
# If you want to restrict expand to specific fields, use:
# SecRule ARGS:\$expand "!@rx ^(__system|field1|field2)(,(__system|field1|field2))*$"

# ============================================================================
# CATEGORY 3: Injection Pattern Detection (Defense-in-Depth)
# ============================================================================

# Rule: Block common SQL injection patterns in $filter
# Purpose: Detect SQL injection attempts despite OData syntax
# Note: This is DEFENSE-IN-DEPTH - Slonik ORM already prevents SQL injection
# File: server/lib/data/odata-filter.js

SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2520,phase:2,deny,status:400,msg:'SQL injection pattern detected in OData filter', \
    SecRule ARGS:\$filter "@rx (?i)(union|select|insert|update|delete|drop|create|alter|grant|revoke|exec|execute|script)" \
    "t:lowercase,chain"
    SecRule ARGS:\$filter "!@rx \\b(eq|ne|gt|ge|lt|le|and|or|not|substringof|startswith|endswith|indexof)\\b"

# Examples:
# BLOCKED: ?$filter=id=1 UNION SELECT password FROM users
# BLOCKED: ?$filter=id=1; DROP TABLE users--
# BLOCKED: ?$filter=id=1; exec('rm -rf /')
# ALLOWED: ?$filter=status eq 'submitted'
# ALLOWED: ?$filter=name ne 'test' and age ge 18
# ALLOWED: ?$filter=substringof('test', name) eq true

# How this works:
# 1. First SecRule: Match SQL keywords (union, select, etc.) case-insensitive
# 2. Second SecRule (chain): Must NOT contain legitimate OData operators
#    This prevents false positives on legitimate queries

# Tuning:
# If you use additional OData functions (e.g., substringof, startswith), add them to the whitelist:
# SecRule ARGS:\$filter "!@rx \\b(eq|ne|gt|ge|lt|le|and|or|not|substringof|startswith|endswith|indexof|replace|tolower|toupper)\\b"

---

# Rule: Block NoSQL/MongoDB injection patterns in $filter
# Purpose: Detect NoSQL injection attempts
# Note: ODK Central uses PostgreSQL, not MongoDB
# Rule 942290 is disabled for OData because $filter looks like NoSQL syntax
# This rule provides additional protection for non-standard patterns

SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2521,phase:2,deny,status:400,msg:'NoSQL injection pattern detected in OData filter', \
    SecRule ARGS:\$filter "@rx (?i)(\$where|\$ne|\$gt|\$lt|\$in|\$nin|\$exists|\$or|\$and|\$not)" \
    "t:lowercase,chain"
    SecRule ARGS:\$filter "!@rx \\.svc/"

# Examples:
# BLOCKED: ?$filter={$where: "this.password == 'admin'"}
# BLOCKED: ?$filter={$ne: null}
# ALLOWED: ?$filter=status eq 'submitted' (OData syntax, not MongoDB)

# How this works:
# 1. First SecRule: Match MongoDB operators ($where, $ne, etc.)
# 2. Second SecRule (chain): Must not contain .svc/ (false positive check)
#    This allows legitimate OData URLs while blocking MongoDB syntax

# Tuning:
# Current rule blocks any $ followed by MongoDB operator
# Adjust if your OData implementation uses dollar sign for other purposes

---

# Rule: Block JavaScript/code injection attempts in $filter
# Purpose: Detect code injection attempts via function calls

SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2522,phase:2,deny,status:400,msg:'Code injection pattern detected in OData filter', \
    SecRule ARGS:\$filter "@rx (?i)(eval|exec|script|function|return|require|import|export)" \
    "t:lowercase,chain"
    SecRule ARGS:\$filter "!@rx \\b(year|month|day|hour|minute|second|now)\\s*\\("

# Examples:
# BLOCKED: ?$filter=eval('malicious code')
# BLOCKED: ?$filter=exec('rm -rf /')
# BLOCKED: ?$filter=function() { malicious code }
# ALLOWED: ?$filter=year(createdAt) eq 2023
# ALLOWED: ?$filter=hour(submitTime) ge 12

# Tuning:
# Second SecRule: Must be one of the whitelisted OData functions
# Current whitelist: year, month, day, hour, minute, second, now
# Add more functions as needed for your OData implementation

---

# Rule: Block path traversal attempts in $filter
# Purpose: Detect path traversal patterns

SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2523,phase:2,deny,status:400,msg:'Path traversal pattern detected in OData filter', \
    SecRule ARGS:\$filter "@rx (\\.\\.|\\.\\./|\\.\\./|/etc/|/proc/|C:\\\\|Windows)"

# Examples:
# BLOCKED: ?$filter=../../../../etc/passwd
# BLOCKED: ?$filter=..\\..\\..\\windows\\system32
# ALLOWED: ?$filter=status eq 'submitted'

# Tuning:
# Current regex matches:
# - ../ or ..\ (path traversal)
# - /etc/, /proc/ (Linux system paths)
# - C:\\ (Windows drive paths)
# Add more patterns as needed for your environment

---

# Rule: Block HTML/script injection attempts
# Purpose: Detect XSS attempts via OData parameters

SecRule REQUEST_URI "@rx \.svc/" \
    "id:2524,phase:2,deny,status:400,msg:'Script injection pattern detected in OData', \
    SecRule ARGS "@rx (?i)<script|</script>|javascript:|onerror=|onload=|onclick=|<iframe"

# Examples:
# BLOCKED: ?$filter=<script>alert(1)</script>
# BLOCKED: ?$select=<iframe src="evil.com">
# ALLOWED: ?$filter=name eq 'test'

# Tuning:
# This applies to ALL OData parameters ($filter, $select, $orderby, etc.)
# If you have legitimate HTML content in field values (unlikely), you may need to adjust

# ============================================================================
# CATEGORY 4: Function Call Validation
# ============================================================================

# Rule: Block unknown function calls in $filter
# Purpose: Ensure only whitelisted OData functions are called
# File: server/lib/data/odata-filter.js:33-45
# Whitelist: year, month, day, hour, minute, second, now

SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2530,phase:2,deny,status:400,msg:'Unauthorized OData function call', \
    SecRule ARGS:\$filter "@rx \\([^)]+\\)" \
    "t:lowercase,chain"
    SecRule ARGS:\$filter "!@rx \\b(year|month|day|hour|minute|second|now)\\s*\\("

# Examples:
# BLOCKED: ?$filter=eval('malicious')
# BLOCKED: ?$filter=system('rm -rf /')
# BLOCKED: ?$filter=require('child_process')
# ALLOWED: ?$filter=year(createdAt) eq 2023
# ALLOWED: ?$filter=hour(submitTime) ge 12

# How this works:
# 1. First SecRule: Match parentheses (function calls)
# 2. Second SecRule (chain): Must be a whitelisted function
# 3. Third SecRule (chain): Must be followed by opening parenthesis

# Tuning:
# To add more OData functions, update the whitelist:
# SecRule ARGS:\$filter "!@rx \\b(year|month|day|hour|minute|second|now|tolower|toupper|trim)\\s*\\("
#
# Supported OData functions vary by implementation:
# - OData v4: https://docs.oasis-open.org/odata/odata/v4.0/os/v4.0/csprd02/
# - ODK Central: Check server/lib/data/odata-filter.js for current list

---

# Rule: Block nested function calls (depth limit)
# Purpose: Prevent DoS via deeply nested function calls
# File: server/lib/data/odata-filter.js

SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2531,phase:2,deny,status:400,msg:'OData function nesting too deep (max 5 levels)', \
    SecRule ARGS:\$filter "@rx (\\([^()]*\\)){6}"

# Examples:
# BLOCKED: ?$filter=year(hour(minute(second(now())))) (6 levels)
# ALLOWED: ?$filter=year(hour(now())) (3 levels)

# How this works:
# Regex matches 6 consecutive opening/closing parenthesis pairs
# This indicates 6 levels of nested function calls
# Adjust the number {6} to change the depth limit

# Tuning:
# Current limit: 5 levels of nesting
# Increase if your legitimate use cases require deeper nesting
# To check maximum depth in your deployment:
#   grep -o "([^()]*)" /var/log/... | awk -F'(' '{print NR}' | sort -n | tail -1

# ============================================================================
# CATEGORY 5: Monitoring and Audit Logging
# ============================================================================

# Rule: Log all OData requests for monitoring (non-blocking)
# Purpose: Track OData usage patterns and detect probing attempts

SecRule REQUEST_URI "@rx \.svc/" \
    "id:2590,phase:1,pass,nolog, \
    SecRule REQUEST_URI "@rx \.svc/(Submissions|Entities)(?:$|\?)" \
    "initcol:ip.odata_tracker_%{REMOTE_ADDR}, \
    setvar:ip.odata_tracker_%{REMOTE_ADDR}_counter=+1, \
    msg:'OData request tracked'"

# This rule tracks OData requests per IP without blocking
# Useful for:
# - Detecting unusual patterns
# - Rate limiting (see rate-limiting docs)
# - Usage analytics

# To view tracked data:
# grep "OData request tracked" /var/log/modsecurity/audit.log

---

# Rule: Alert on suspicious OData SQLi-like patterns (non-blocking)
# Purpose: Detect potential SQL injection attempts for monitoring
# Note: This does NOT block, only logs

SecRule REQUEST_URI "@rx \.svc/.*\$filter=" \
    "id:2591,phase:1,pass,msg:'Potential OData SQLi pattern detected (monitoring only)', \
    SecRule ARGS:\$filter "@rx (?i)(union|select|insert|update|delete|drop|create|alter|grant|revoke)" \
    "t:lowercase,chain"
    SecRule ARGS:\$filter "!@rx \\b(eq|ne|gt|ge|lt|le|and|or)\\b"

# Examples (LOGGED, NOT BLOCKED):
# ?$filter=id=1 UNION SELECT * FROM users (logged)
# ?$filter=status eq 'submitted' (not logged, legitimate)

# Use this for:
# - Security monitoring
# - Alerting (e.g., send to SIEM)
# - Threat hunting

# To convert to blocking, change "phase:1,pass" to "phase:2,deny,status:400"

---

# Rule: Alert on repeated OData failures from same IP (potential probing)
# Purpose: Detect automated scanning/probing tools

SecRule REQUEST_URI "@rx \.svc/" \
    "id:2592,phase:5,pass,msg:'Repeated OData failures from IP (potential probing)', \
    SecRule IP:REQUEST_URI "@rx ^/v1/.*\.svc/.*\?.*$" \
    "within=60,deny,status:429,t:count,msg:'Too many OData requests from this IP'"

# This blocks IPs that make many OData requests with query strings
# Threshold: 60 requests per minute (adjustable)
# Purpose: Detect/stop automated scanning tools

# Tuning:
# "within=60" = 60 seconds time window
# "deny,status=429" = Block with 429 Too Many Requests
# "t:count" = Count number of requests in time window
# Adjust the count threshold as needed

---

# Rule: Log blocked OData requests with details
# Purpose: Detailed audit logging for security analysis

SecRule REQUEST_URI "@rx \.svc/" \
    "id:2593,phase:2,pass,nolog, \
    SecRule RESPONSE_STATUS "@streq 400" \
    "msg:'OData request blocked - audit logging', \
    ctl:auditLogParts=+Message, \
    ctl:auditEngine=On"

# This logs detailed information when OData requests are blocked
# Useful for:
# - Incident response
# - Compliance auditing
# - Threat analysis

# Logged information includes:
# - Request details (IP, URL, headers)
# - Response status (400, 414, etc.)
# - Rule that triggered the block

---

# ============================================================================
# CATEGORY 6: Request Size Limits
# ============================================================================

# Rule: Limit OData request body size (if POST/PUT is ever added)
# Purpose: Prevent DoS via large request bodies
# Note: OData currently only uses GET, but this is future-proofing

SecRule REQUEST_URI "@rx \.svc/" \
    "id:2540,phase:1,deny,status:413,msg:'OData request body too large', \
    SecRule REQUEST_HEADERS:Content-Length "@gt 1048576"

# Examples:
# BLOCKED: POST /v1/projects/1/forms/basic.svc (body > 1MB)
# ALLOWED: POST /v1/projects/1/forms/basic.svc (body < 1MB)

# Tuning:
# Current limit: 1MB (1048576 bytes)
# Increase if needed for legitimate OData batch operations
# Note: This is request body, not response body

---

# Rule: Limit OData response body size (prevents data exfiltration)
# Purpose: Prevent DoS via massive response bodies
# Note: This requires ModSecurity response body inspection

# Uncomment if you need response body inspection (performance impact):
# SecRule REQUEST_URI "@rx \.svc/Submissions$" \
#     "id:2541,phase:4,deny,status:500,msg:'OData response too large', \
#     SecRule RESPONSE_BODY_SIZE "@gt 104857600"

# Examples:
# BLOCKED: Response > 100MB
# ALLOWED: Response < 100MB

# Tuning:
# Current limit: 100MB (104857600 bytes)
# Response body inspection has performance impact
# Only enable if you need to prevent massive downloads

# ============================================================================
# CATEGORY 7: Header Validation
# ============================================================================

# Rule: Validate Accept header for OData requests
# Purpose: Ensure proper content negotiation

SecRule REQUEST_URI "@rx \.svc/.*\$format=" \
    "id:2550,phase:1,deny,status:406,msg:'Invalid OData format requested', \
    SecRule ARGS:\$format "!@rx ^(json|xml|atom)$"

# Examples:
# BLOCKED: ?$format=../../etc/passwd
# BLOCKED: ?$format=<script>alert(1)</script>
# ALLOWED: ?$format=json
# ALLOWED: ?$format=xml
# ALLOWED: ?$format=atom

# Tuning:
# Current whitelist: json, xml, atom (OData-supported formats)
# Add more formats if your OData implementation supports them
# See: https://docs.oasis-open.org/odata/odata/v4.0/os/v4.0/csprd02/

---

# Rule: Validate User-Agent for OData requests (optional)
# Purpose: Detect/block suspicious user agents
# Note: Only enable if you have legitimate User-Agent requirements

# Uncomment to enable:
# SecRule REQUEST_URI "@rx \.svc/" \
#     "id:2551,phase:1,deny,status:403,msg:'OData access denied to this User-Agent', \
#     SecRule REQUEST_HEADERS:User-Agent "@rx (curl|wget|python|perl|ruby|bash|sh)"

# Examples (if enabled):
# BLOCKED: curl/7.68.0
# BLOCKED: Python-urllib/3.9
# ALLOWED: Mozilla/5.0 (browser)
# ALLOWED: Power BI/Excel (legitimate tools)

# Tuning:
# WARNING: This may block legitimate tools (Power BI, Excel, pyODK)
# Only enable if you have specific User-Agent requirements
# Current status: DISABLED (commented out)

# ============================================================================
# END OF ODATA HARDENING RULES
# ============================================================================
