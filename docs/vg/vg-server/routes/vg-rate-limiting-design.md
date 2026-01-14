# VG Modular Rate Limiting Design

> **Last Updated:** 2026-01-14
> **Purpose:** Modular rate limiting system following VG auth pattern
> **Status:** Design Recommendation

---

## Overview

This document proposes a modular rate limiting system for ODK Central, following the established VG fork pattern used for authentication (web-user and app-user auth).

### Why Modular?

Following the existing VG pattern provides:
- ✅ **Consistency** - Same architecture as existing VG features
- ✅ **Configurability** - Project-level settings overrides
- ✅ **Maintainability** - Separation of concerns (domain/model/resources)
- ✅ **Testability** - Each layer can be tested independently
- ✅ **Extensibility** - Easy to add new rate-limited endpoints

---

## Current VG Auth Pattern Reference

### Architecture Layers

```
server/lib/
├── domain/
│   └── vg-app-user-auth.js       # Business logic, validation, orchestration
├── model/query/
│   ├── vg-app-user-auth.js       # Database queries for auth
│   └── vg-app-user-ip-rate-limit.js  # IP rate limiting queries
├── model/
│   └── frames/vg-app-user-auth.js  # Data structures
├── resources/
│   └── vg-app-user-auth.js       # HTTP endpoints
└── util/
    └── vg-password.js            # Utilities
```

### Settings Pattern

Settings stored in `vg_settings` table with project-level overrides:

```sql
-- Global default
INSERT INTO vg_settings (key, value) VALUES ('vg_app_user_lock_max_failures', '5');

-- Project override
INSERT INTO vg_project_settings (project_id, key, value)
VALUES (123, 'vg_app_user_lock_max_failures', '10');
```

### Example: App User IP Rate Limiting

**Domain Layer** (`server/lib/domain/vg-app-user-auth.js`):
```javascript
const getLockConfig = async (VgAppUserAuth, projectId) => {
  const [maxFailures, windowMinutes, durationMinutes] = await Promise.all([
    VgAppUserAuth.getSettingWithProjectOverride(projectId, 'vg_app_user_lock_max_failures', DEFAULT_LOCK_MAX_FAILURES),
    VgAppUserAuth.getSettingWithProjectOverride(projectId, 'vg_app_user_lock_window_minutes', DEFAULT_LOCK_WINDOW_MINUTES),
    VgAppUserAuth.getSettingWithProjectOverride(projectId, 'vg_app_user_lock_duration_minutes', DEFAULT_LOCK_DURATION_MINUTES)
  ]);
  return { maxFailures, windowMinutes, durationMinutes };
};
```

**Query Layer** (`server/lib/model/query/vg-app-user-ip-rate-limit.js`):
```javascript
const isAppUserIpLocked = (ip, lockDurationMinutes = DEFAULT_IP_LOCK_DURATION_MINUTES) => ({ maybeOne }) => {
  if (ip == null) return Promise.resolve(false);
  return getLatestAppUserIpLockoutAt(ip)({ maybeOne })
    .then((lockedAt) => {
      if (lockedAt == null) return false;
      const remainingMs = new Date(lockedAt).getTime() + (lockDurationMinutes * 60 * 1000) - Date.now();
      if (remainingMs <= 0) return false;
      const error = new Problem(429.7, 'Too many login attempts from your location. Please try again later.', {
        retryAfterSeconds: Math.ceil(remainingMs / 1000)
      });
      throw error;
    });
};
```

---

## Proposed Modular Rate Limiting System

### File Structure

```
server/lib/
├── domain/
│   └── vg-rate-limit.js              # Domain logic: orchestration, validation
├── model/query/
│   └── vg-rate-limit.js              # Database queries: audits table queries
├── middleware/
│   └── vg-rate-limit.js              # Express middleware for endpoint protection
└── resources/
    └── (existing files use middleware) # Apply to OData, submissions, etc.
```

### Database Schema

**Use existing `audits` table** (no new tables needed):

```sql
-- Rate limit tracking via audits table
-- Each request logged as an audit entry
-- Count queries by action + identifier + time window

SELECT count(*) AS count
FROM audits
WHERE action = 'vg.rate_limit.odata.read'
  AND details->>'identifier' = 'user_123_project_456'
  AND "loggedAt" >= now() - interval '1 minute';
```

### Settings Table

**New settings in `vg_settings`:**

```sql
-- Global defaults
INSERT INTO vg_settings (key, value, description) VALUES
  ('vg_rate_limit_enabled', 'true', 'Enable/disable rate limiting globally'),
  ('vg_rate_limit_odata_per_minute', '100', 'OData requests per minute per user'),
  ('vg_rate_limit_submission_per_minute', '50', 'Submission uploads per minute per IP'),
  ('vg_rate_limit_formlist_per_minute', '20', 'Form list requests per minute per IP'),
  ('vg_rate_limit_project_per_minute', '200', 'General API requests per minute per project'),
  ('vg_rate_limit_window_seconds', '60', 'Rate limit time window in seconds'),
  ('vg_rate_limit_burst_size', '10', 'Token bucket burst size');

-- Project-specific overrides (example)
INSERT INTO vg_project_settings (project_id, key, value) VALUES
  (123, 'vg_rate_limit_odata_per_minute', '50'),   -- Stricter for this project
  (456, 'vg_rate_limit_enabled', 'false');          -- Disabled for this project
```

---

## Implementation

### 1. Domain Layer (`server/lib/domain/vg-rate-limit.js`)

```javascript
// Domain logic for VG rate limiting
const Problem = require('../util/problem');

const DEFAULT_LIMITS = {
  odata_per_minute: 100,
  submission_per_minute: 50,
  formlist_per_minute: 20,
  project_per_minute: 200,
  window_seconds: 60,
  burst_size: 10
};

const getRateLimitConfig = async (VgRateLimit, projectId, endpointType) => {
  const settingKey = `vg_rate_limit_${endpointType}_per_minute`;
  const limit = await VgRateLimit.getSettingWithProjectOverride(
    projectId,
    settingKey,
    DEFAULT_LIMITS[`${endpointType}_per_minute`]
  );
  const windowSeconds = await VgRateLimit.getSettingWithProjectOverride(
    projectId,
    'vg_rate_limit_window_seconds',
    DEFAULT_LIMITS.window_seconds
  );
  return { limit, windowSeconds };
};

const checkRateLimit = async (container, action, identifier, projectId, endpointType) => {
  const { VgRateLimit } = container;

  // Check if rate limiting is enabled
  const enabled = await VgRateLimit.getSettingWithProjectOverride(
    projectId,
    'vg_rate_limit_enabled',
    'true'
  );
  if (enabled !== 'true') return { allowed: true };

  // Get config for this endpoint type
  const { limit, windowSeconds } = await getRateLimitConfig(VgRateLimit, projectId, endpointType);

  // Check current usage
  const count = await VgRateLimit.getRequestCount(action, identifier, windowSeconds);

  if (count >= limit) {
    const retryAfter = windowSeconds;
    throw Problem.user.rateLimitExceeded({
      retryAfter,
      limit,
      windowSeconds,
      endpointType
    });
  }

  // Log the request
  await VgRateLimit.logRequest(action, identifier);

  return { allowed: true, remaining: limit - count - 1 };
};

module.exports = {
  getRateLimitConfig,
  checkRateLimit,
  DEFAULT_LIMITS
};
```

---

### 2. Query Layer (`server/lib/model/query/vg-rate-limit.js`)

```javascript
// Database queries for VG rate limiting
const { sql } = require('slonik');

const getRequestCount = (action, identifier, windowSeconds) => ({ maybeOne }) =>
  maybeOne(sql`
    SELECT count(*)::int AS count
    FROM audits
    WHERE action = ${action}
      AND details->>'identifier' = ${identifier}
      AND "loggedAt" >= now() - (${windowSeconds} * interval '1 second')
  `).then((opt) => opt.map((row) => row.count).orElse(0));

const logRequest = (Audits, action, identifier, details = {}) => {
  return Audits.log(null, action, null, {
    identifier,
    timestamp: new Date().toISOString(),
    ...details
  });
};

const getSettingWithProjectOverride = (projectId, key, defaultValue) =>
  // Reuse existing VG settings pattern
  // See: server/lib/model/query/vg-app-user-auth.js
  // Implementation queries vg_settings and vg_project_settings tables
  // Returns project-specific value if exists, otherwise global default
  sql`
    COALESCE(
      (SELECT value FROM vg_project_settings WHERE project_id = ${projectId} AND key = ${key}),
      (SELECT value FROM vg_settings WHERE key = ${key}),
      ${defaultValue}
    )::text
  `;

module.exports = {
  getRequestCount,
  logRequest,
  getSettingWithProjectOverride
};
```

---

### 3. Middleware Layer (`server/lib/middleware/vg-rate-limit.js`)

```javascript
// Express middleware for VG rate limiting
const { checkRateLimit } = require('../domain/vg-rate-limit');

const createRateLimitMiddleware = (action, endpointType, getIdentifier) => {
  return async (req, res, next) => {
    try {
      const { auth, params } = req;
      const projectId = params.projectId || params.projectId;

      // Build identifier (can be customized per endpoint)
      const identifier = getIdentifier
        ? getIdentifier(req)
        : `${auth.actor?.id || 'anonymous'}_project_${projectId || 'default'}`;

      await checkRateLimit(
        req.container,
        `vg.rate_limit.${action}`,
        identifier,
        projectId,
        endpointType
      );

      next();
    } catch (error) {
      next(error);
    }
  };
};

// Endpoint-specific middleware factories
const odataRateLimit = () => createRateLimitMiddleware(
  'odata.read',
  'odata',
  (req) => `${req.auth.actor.id}_project_${req.params.projectId}`
);

const submissionRateLimit = () => createRateLimitMiddleware(
  'submission.create',
  'submission',
  (req) => `ip_${req.ip}_project_${req.params.projectId}`
);

const formListRateLimit = () => createRateLimitMiddleware(
  'formlist.read',
  'formlist',
  (req) => `ip_${req.ip}`
);

const projectRateLimit = () => createRateLimitMiddleware(
  'project.read',
  'project',
  (req) => `${req.auth.actor.id}_project_${req.params.projectId}`
);

module.exports = {
  createRateLimitMiddleware,
  odataRateLimit,
  submissionRateLimit,
  formListRateLimit,
  projectRateLimit
};
```

---

## Usage Examples

### Applying to OData Endpoints

**File:** `server/lib/resources/odata.js`

```javascript
const { odataRateLimit } = require('../middleware/vg-rate-limit');

module.exports = (service, endpoint) => {
  const odataResource = (base, draft, getForm) => {
    // Apply rate limiting to all OData endpoints
    service.get(base,
      odataRateLimit(),
      endpoint.odata.json(({ Forms, env }, { auth, params, originalUrl }) =>
        getForm(Forms, auth, params)
          .then((form) => Forms.getFields(form.def.id))
          .then((fields) => serviceDocumentFor(fields, env.domain, originalUrl))
          .then(contentType('application/json; odata.metadata=minimal'))
      )
    );

    // Metadata endpoint
    service.get(`${base}/([$])metadata`,
      odataRateLimit(),
      endpoint.odata.xml(({ Forms }, { auth, params }) =>
        // ... existing code
      )
    );

    // Submissions feed (stricter limit)
    service.get(`${base}/Submissions`,
      odataRateLimit(),
      endpoint.odata.json(({ Forms, Submissions, env }, { auth, params, originalUrl, query }) =>
        // ... existing code
      )
    );
  };
};
```

### Applying to Submission Endpoints

**File:** `server/lib/resources/submissions.js`

```javascript
const { submissionRateLimit } = require('../middleware/vg-rate-limit');

module.exports = (service, endpoint) => {
  // OpenROSA submission endpoint
  service.post('/projects/:projectId/submission',
    submissionRateLimit(),
    endpoint.odata((...) => {
      // ... existing code
    })
  );

  // REST submission endpoint
  service.post('/projects/:projectId/forms/:xmlFormId/submissions',
    submissionRateLimit(),
    endpoint.((...) => {
      // ... existing code
    })
  );
};
```

### Applying to Form List (OpenROSA)

**File:** `server/lib/resources/forms.js`

```javascript
const { formListRateLimit } = require('../middleware/vg-rate-limit');

module.exports = (service, endpoint) => {
  service.get('/projects/:projectId/formList',
    formListRateLimit(),
    endpoint.((...) => {
      // ... existing code
    })
  );
};
```

---

## Configuration

### Environment Variables

```bash
# .env or docker-compose.yml
VG_RATE_LIMIT_ENABLED=true
VG_RATE_LIMIT_ODATA_PER_MINUTE=100
VG_RATE_LIMIT_SUBMISSION_PER_MINUTE=50
VG_RATE_LIMIT_FORMLIST_PER_MINUTE=20
VG_RATE_LIMIT_PROJECT_PER_MINUTE=200
```

### Database Settings

```sql
-- Set global defaults
INSERT INTO vg_settings (key, value) VALUES
  ('vg_rate_limit_enabled', 'true'),
  ('vg_rate_limit_odata_per_minute', '100'),
  ('vg_rate_limit_submission_per_minute', '50'),
  ('vg_rate_limit_formlist_per_minute', '20'),
  ('vg_rate_limit_project_per_minute', '200');

-- Per-project override (stricter for sensitive project)
INSERT INTO vg_project_settings (project_id, key, value) VALUES
  (123, 'vg_rate_limit_odata_per_minute', '10');

-- Per-project disable (trusted project)
INSERT INTO vg_project_settings (project_id, key, value) VALUES
  (456, 'vg_rate_limit_enabled', 'false');
```

---

## WAF Fallback

While the application-level rate limiting is being implemented, use WAF rules as immediate protection:

**File:** `crs_custom/30-vg-rate-limiting.conf`

```nginx
# Temporary WAF rate limiting (until app-level is deployed)
# Will be removed/reduced after modular rate limiting is in place

SecRule REQUEST_URI "@rx \.svc" \
    "id:3010,phase:1,deny,status=429, \
    setvar:ip.odata_counter=+1,expirevar:ip.odata_counter=60, \
    t:count,deny,msg='OData rate limit exceeded (100/60s)'"
```

---

## Advantages Over WAF-Only Rate Limiting

| Feature | WAF-Only | Modular (App-Level) |
|---------|----------|---------------------|
| User-based limits | ❌ No | ✅ Yes |
| Project-based limits | ⚠️ Complex | ✅ Native |
| Role-based limits | ❌ No | ✅ Yes |
| Dynamic configuration | ❌ Requires restart | ✅ Database-driven |
| Per-project overrides | ❌ No | ✅ Yes |
| Audit trail | ❌ Limited | ✅ Full audit log |
| IP-based limits | ✅ Yes | ✅ Yes |
| Performance | ⚠️ Nginx overhead | ⚠️ App overhead |

**Recommendation:** Use both for defense-in-depth:
- WAF for IP-based brute force protection
- App-level for user/project-based limits

---

## Implementation Roadmap

### Phase 1: Database Schema (Day 1)
1. Add settings to `vg_settings` table
2. Document settings in `docs/vg/vg-server/routes/system-settings.md`

### Phase 2: Core Modules (Days 2-3)
1. Create `server/lib/model/query/vg-rate-limit.js`
2. Create `server/lib/domain/vg-rate-limit.js`
3. Create `server/lib/middleware/vg-rate-limit.js`
4. Unit tests for each module

### Phase 3: Endpoint Integration (Days 4-5)
1. Apply to OData endpoints
2. Apply to submission endpoints
3. Apply to form list endpoint
4. Integration tests

### Phase 4: Configuration & Testing (Day 6)
1. Add database migrations
2. Add admin UI for settings (optional)
3. Load testing
4. Documentation updates

### Phase 5: Deployment (Day 7)
1. Deploy with WAF fallback in place
2. Monitor for false positives
3. Adjust limits based on traffic patterns
4. Remove/reduce WAF rules after validation

---

## Testing Strategy

### Unit Tests

```javascript
// test/unit/model/query/vg-rate-limit.test.js
describe('VgRateLimit', () => {
  it('should count requests in time window', async () => {
    const count = await VgRateLimit.getRequestCount(
      'vg.rate_limit.odata.read',
      'user_1_project_1',
      60
    )({ maybeOne: mockMaybeOne });
    assert.equal(count, 0);
  });
});
```

### Integration Tests

```javascript
// test/integration/api/vg-rate-limiting.test.js
describe('OData Rate Limiting', () => {
  it('should allow requests under limit', async () => {
    for (let i = 0; i < 99; i++) {
      await agent.get('/v1/projects/1/forms/basic.svc')
        .expect(200);
    }
  });

  it('should block requests over limit', async () => {
    for (let i = 0; i < 100; i++) {
      await agent.get('/v1/projects/1/forms/basic.svc');
    }
    await agent.get('/v1/projects/1/forms/basic.svc')
      .expect(429)
      .expect('Retry-After', '60');
  });
});
```

### Load Tests

```bash
# Use artillery or k6 for load testing
# Test that rate limiting works under load
artillery run test/load/rate-limit.yml
```

---

## Migration Path

**Step 1:** Deploy WAF rate limiting (immediate protection)
**Step 2:** Deploy modular rate limiting alongside WAF
**Step 3:** Monitor for 1-2 weeks
**Step 4:** Reduce/remove WAF rules after validation

---

## Related Documentation

- **Main WAF Inventory:** `docs/vg/modsecurity-waf-api-inventory.md`
- **OData Endpoints:** `docs/vg/vg-server/routes/odata-endpoints.md`
- **App User Auth:** `docs/vg/vg-server/routes/app-user-auth.md`
- **Web User Hardening:** `docs/vg/vg-server/routes/web-user-hardening.md`
- **System Settings:** `docs/vg/vg-server/routes/system-settings.md`

---

## Verification Checklist

- [ ] Design follows VG auth pattern
- [ ] Settings in `vg_settings` table
- [ ] Project-level overrides supported
- [ ] Uses existing `audits` table
- [ ] Middleware layer for endpoint protection
- [ ] WAF fallback for immediate protection
- [ ] Unit tests planned
- [ ] Integration tests planned
- [ ] Load tests planned
- [ ] Documentation updated
