# ODK Central Configuration: Environment Variables vs Templates

**Understanding how stock ODK Central and VG fork handle configuration from environment variables.**

---

## Overview

ODK Central supports **two approaches** for loading configuration from environment variables:

1. **Stock ODK Central**: Template substitution at container startup
2. **VG Fork Enhancement**: `node-config` environment variable mapping

Both approaches work and can coexist. This document explains when and why to use each.

---

## Stock ODK Central Approach (Template-Based)

### How It Works

**At container startup** (`files/service/scripts/start-odk.sh`):

```bash
ENKETO_API_KEY=$(cat /etc/secrets/enketo-api-key) \
BASE_URL=$( [ "${HTTPS_PORT}" = 443 ] && echo https://"${DOMAIN}" || echo https://"${DOMAIN}":"${HTTPS_PORT}" ) \
/scripts/envsub.awk \
    < /usr/share/odk/config.json.template \
    > /usr/odk/config/local.json
```

**Process:**
```
┌─────────────────────────────────────────────────┐
│  Container Starts                               │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  Read: /usr/share/odk/config.json.template      │
│  {                                              │
│    "database": {                                │
│      "host": "${DB_HOST}",                      │
│      "password": "${DB_PASSWORD}"               │
│    },                                           │
│    "s3blobStore": {                             │
│      "server": "${S3_SERVER}",                  │
│      "accessKey": "${S3_ACCESS_KEY}"            │
│    }                                            │
│  }                                              │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  envsub.awk substitutes ${VAR} with env values  │
│  - DB_HOST → postgres14                         │
│  - DB_PASSWORD → odk                            │
│  - S3_SERVER → https://s3.central.local         │
│  - S3_ACCESS_KEY → GK73ce...                    │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  Write: /usr/odk/config/local.json              │
│  {                                              │
│    "database": {                                │
│      "host": "postgres14",                      │
│      "password": "odk"                          │
│    },                                           │
│    "s3blobStore": {                             │
│      "server": "https://s3.central.local",      │
│      "accessKey": "GK73ce..."                   │
│    }                                            │
│  }                                              │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  node-config reads /usr/odk/config/local.json   │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  Application gets configuration                 │
└─────────────────────────────────────────────────┘
```

### Template File (`files/service/config.json.template`)

```json
{
  "default": {
    "database": {
      "host": "${DB_HOST}",
      "user": "${DB_USER}",
      "password": "${DB_PASSWORD}",
      "database": "${DB_NAME}",
      "ssl": ${DB_SSL},
      "maximumPoolSize": ${DB_POOL_SIZE}
    },
    "email": {
      "serviceAccount": "${EMAIL_FROM}",
      "transportOpts": {
        "host": "${EMAIL_HOST}",
        "port": ${EMAIL_PORT}
      }
    },
    "external": {
      "s3blobStore": {
        "server": "${S3_SERVER}",
        "accessKey": "${S3_ACCESS_KEY}",
        "secretKey": "${S3_SECRET_KEY}",
        "bucketName": "${S3_BUCKET_NAME}",
        "requestTimeout": 60000
      }
    }
  }
}
```

### The `envsub.awk` Script

**Location:** `files/shared/envsub.awk`

**Key features:**
- Safer than standard `envsubst`
- **Requires:** `${UPPERCASE_NAME}` format (curly braces + uppercase)
- **Validates:** Fails if environment variable is not defined
- **No silent failures:** Won't substitute with empty string

**Example:**
```bash
# Template has:
"host": "${DB_HOST}"

# If DB_HOST is not set:
❌ ERROR: var not defined: ${DB_HOST}
exit 1

# If DB_HOST=postgres14:
✅ "host": "postgres14"
```

### Pros and Cons

**Advantages:**
- ✅ **Explicit and visible**: Template shows exactly what's being substituted
- ✅ **Container immutability**: local.json regenerated on every start
- ✅ **No hardcoded secrets**: Generated file never committed to git
- ✅ **Validation**: Fails fast if required env vars missing

**Disadvantages:**
- ❌ **Startup dependency**: Requires Docker container startup script
- ❌ **Doesn't work in development**: Local `npm start` won't generate file
- ❌ **Manual restart needed**: Changes require container restart

---

## VG Fork Approach (node-config Environment Variables)

### How It Works

**Uses `node-config`'s built-in environment variable mapping.**

**At application runtime:**

```
┌─────────────────────────────────────────────────┐
│  Application Starts (npm start / node)          │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  node-config loads configuration hierarchy:     │
│  1. config/default.json                         │
│  2. config/local.json                           │
│  3. config/custom-environment-variables.json    │
│  4. Environment variables                       │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  custom-environment-variables.json maps:        │
│  {                                              │
│    "database": {                                │
│      "host": "DB_HOST",         ← env var name  │
│      "password": "DB_PASSWORD"                  │
│    },                                           │
│    "s3blobStore": {                             │
│      "server": "S3_SERVER",                     │
│      "accessKey": "S3_ACCESS_KEY"               │
│    }                                            │
│  }                                              │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  node-config reads process.env:                 │
│  - process.env.DB_HOST → "postgres14"           │
│  - process.env.S3_SERVER → "https://s3..."      │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│  Final config returned to application           │
│  config.get('default.database.host')            │
│    → "postgres14" (from process.env.DB_HOST)    │
└─────────────────────────────────────────────────┘
```

### Mapping File (`server/config/custom-environment-variables.json`)

```json
{
  "default": {
    "database": {
      "host": "DB_HOST",
      "user": "DB_USER",
      "password": "DB_PASSWORD",
      "database": "DB_NAME",
      "ssl": "DB_SSL",
      "maximumPoolSize": {
        "__name": "DB_POOL_SIZE",
        "__format": "number"
      }
    },
    "external": {
      "s3blobStore": {
        "server": "S3_SERVER",
        "accessKey": "S3_ACCESS_KEY",
        "secretKey": "S3_SECRET_KEY",
        "bucketName": "S3_BUCKET_NAME",
        "requestTimeout": {
          "__name": "S3_REQUEST_TIMEOUT",
          "__format": "number"
        }
      }
    },
    "sessionLifetime": {
      "__name": "SESSION_LIFETIME",
      "__format": "number"
    }
  }
}
```

**Mapping syntax:**
- **Simple:** `"configKey": "ENV_VAR_NAME"`
- **Typed:** `"configKey": { "__name": "ENV_VAR", "__format": "number|boolean" }`

### Configuration Priority Order

`node-config` merges in this order (**highest priority last**):

```
1. config/default.json           (lowest priority)
   ↓
2. config/{environment}.json     (e.g., production.json)
   ↓
3. config/local.json              (local overrides)
   ↓
4. Environment Variables          (HIGHEST PRIORITY)
   (via custom-environment-variables.json)
```

**Example:**

```json
// default.json
{ "database": { "host": "localhost" } }

// local.json
{ "database": { "host": "postgres14" } }

// custom-environment-variables.json
{ "database": { "host": "DB_HOST" } }

// process.env.DB_HOST = "prod-db.example.com"

// Final result:
config.get('database.host') → "prod-db.example.com"
```

### Pros and Cons

**Advantages:**
- ✅ **Standard pattern**: Official `node-config` feature
- ✅ **Works everywhere**: Docker, local development, test environments
- ✅ **No startup script**: Works immediately when app starts
- ✅ **Runtime flexibility**: Can change env vars without rebuild
- ✅ **Type safety**: Built-in type coercion (number, boolean)

**Disadvantages:**
- ❌ **Less visible**: Need to understand node-config hierarchy
- ❌ **Silent fallbacks**: Missing env var → uses local.json value
- ❌ **Requires knowledge**: Developers must understand node-config

---

## Comparison Table

| Feature | Stock ODK (Template) | VG Fork (node-config) |
|---------|----------------------|-----------------------|
| **When substitution happens** | Container startup (one-time) | Application runtime (every start) |
| **Mechanism** | `envsub.awk` script | `node-config` library |
| **Config file modified** | `local.json` (generated) | None (read-only mapping) |
| **Works in Docker** | ✅ Yes | ✅ Yes |
| **Works in local dev** | ❌ No | ✅ Yes |
| **Requires restart** | Container restart | Process restart |
| **Validation** | Fails if var missing | Uses fallback |
| **Standard pattern** | Custom ODK solution | Standard node-config |
| **Git-tracked files** | Template only | Mapping file |

---

## Security Implications

### ❌ NEVER Hardcode Secrets in `local.json`

**Bad example:**
```json
// server/config/local.json ❌ DO NOT DO THIS
{
  "external": {
    "s3blobStore": {
      "server": "https://s3.example.com",
      "accessKey": "AKIAIOSFODNN7EXAMPLE",      // ❌ SECRET IN GIT!
      "secretKey": "wJalrXUtnFEMI/K7MDENG/..."  // ❌ VERY BAD!
    }
  }
}
```

**Why this is dangerous:**
- 🔴 Git history contains secrets **forever**
- 🔴 Anyone with repo access gets production credentials
- 🔴 Difficult to rotate credentials (requires code change)
- 🔴 Violates 12-factor app principles
- 🔴 Compliance violations (SOC2, PCI-DSS, etc.)

### ✅ Correct Approach: Environment Variables Only

**Stock ODK (Template):**
```json
// files/service/config.json.template ✅ CORRECT
{
  "s3blobStore": {
    "server": "${S3_SERVER}",      // Placeholder, not secret
    "accessKey": "${S3_ACCESS_KEY}"
  }
}
```

**VG Fork (Mapping):**
```json
// server/config/custom-environment-variables.json ✅ CORRECT
{
  "s3blobStore": {
    "server": "S3_SERVER",      // Mapping, not value
    "accessKey": "S3_ACCESS_KEY"
  }
}
```

**Both read from `.env` (NOT tracked in git):**
```bash
# .env (add to .gitignore)
S3_SERVER=https://s3.example.com
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/...
```

---

## VG Fork Strategy: Best of Both Worlds

**We use BOTH approaches** for maximum compatibility:

### 1. Template-Based (Stock ODK Compatibility)

**Kept from upstream:**
- `files/service/config.json.template` ✅
- `files/service/scripts/start-odk.sh` ✅
- `files/shared/envsub.awk` ✅

**Benefit:** Docker deployments work exactly like stock ODK Central.

### 2. node-config Mapping (VG Enhancement)

**Added in VG fork:**
- `server/config/custom-environment-variables.json` ✅

**Benefit:** Local development and testing work without Docker.

### 3. Empty local.json (Security)

**VG practice:**
- `server/config/local.json` → `"s3blobStore": {}` (empty)

**Benefit:** No secrets in git-tracked files.

### How They Work Together

```
Docker Container Startup:
  1. start-odk.sh runs envsub.awk
  2. Generates local.json with actual values
  3. node-config reads local.json
  4. custom-environment-variables.json unused (local.json already populated)

Local Development (npm start):
  1. No startup script runs
  2. local.json remains empty
  3. node-config reads custom-environment-variables.json
  4. Maps environment variables to config
```

**Result:** Works in **both** Docker and local environments! 🎯

---

## Usage Examples

### Docker Deployment (Uses Template)

```bash
# .env file
DB_HOST=postgres14
S3_SERVER=https://s3.example.com
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE

# Start container
docker compose up -d service

# Inside container at startup:
# 1. envsub.awk reads config.json.template
# 2. Replaces ${S3_SERVER} with "https://s3.example.com"
# 3. Writes to config/local.json
# 4. Application reads local.json
```

### Local Development (Uses node-config Mapping)

```bash
# .env file
DB_HOST=localhost
S3_SERVER=http://localhost:9000
S3_ACCESS_KEY=minioadmin

# Load env vars
export $(grep -v '^#' .env | xargs)

# Start app
cd server && npm start

# Application flow:
# 1. node-config loads custom-environment-variables.json
# 2. Reads process.env.S3_SERVER
# 3. Maps to config.get('default.external.s3blobStore.server')
```

### Testing (Uses node-config Mapping)

```bash
# Set test env vars
export NODE_CONFIG_ENV=test
export DB_HOST=localhost
export S3_SERVER=http://localhost:9000

# Run tests
npm test

# node-config:
# 1. Loads config/test.json
# 2. Loads custom-environment-variables.json
# 3. Reads test-specific env vars
```

---

## Troubleshooting

### "Config value is undefined"

**Symptom:** `config.get('default.external.s3blobStore.server')` returns `undefined`

**Diagnosis:**
```bash
# Check if env var is set
echo $S3_SERVER

# Check if Docker is passing env var
docker compose config | grep S3_SERVER

# Check if custom-environment-variables.json exists
ls -la server/config/custom-environment-variables.json
```

**Solution:**
1. Ensure env var is exported: `export S3_SERVER=...`
2. Ensure docker-compose.yml passes it: `- S3_SERVER=${S3_SERVER:-}`
3. Ensure mapping exists in custom-environment-variables.json

### "Template variable not substituted"

**Symptom:** local.json contains `"${S3_SERVER}"` instead of actual value

**Diagnosis:**
```bash
# Check if envsub.awk ran
docker compose logs service | grep "generating local service configuration"

# Check if env var is set in container
docker compose exec service printenv | grep S3_SERVER
```

**Solution:**
1. Ensure .env file exists and contains S3_SERVER
2. Ensure docker-compose.yml passes env var to service
3. Restart container: `docker compose restart service`

### "Secrets in git history"

**Symptom:** `git log -p` shows hardcoded credentials in local.json

**Solution:**
```bash
# Remove from history (DANGEROUS - coordinate with team!)
git filter-branch --tree-filter 'git rm -f --ignore-unmatch server/config/local.json' HEAD

# Or use git-filter-repo (recommended)
git filter-repo --path server/config/local.json --invert-paths

# Rotate compromised credentials immediately!
```

---

## Migration Guide

### From Hardcoded local.json to Environment Variables

**Step 1:** Create `custom-environment-variables.json` (already done in VG fork)

**Step 2:** Extract secrets from local.json to .env
```bash
# Before: server/config/local.json
{
  "s3blobStore": {
    "server": "https://s3.example.com",
    "accessKey": "AKIAIOSFODNN7EXAMPLE"
  }
}

# After: .env (not tracked in git)
S3_SERVER=https://s3.example.com
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE

# After: server/config/local.json
{
  "s3blobStore": {}
}
```

**Step 3:** Update docker-compose.yml (already done in VG fork)
```yaml
service:
  environment:
    - S3_SERVER=${S3_SERVER:-}
    - S3_ACCESS_KEY=${S3_ACCESS_KEY:-}
```

**Step 4:** Test
```bash
# Restart service
docker compose restart service

# Verify config loaded
docker compose exec service node -e "const config = require('config'); console.log(config.get('default.external.s3blobStore'))"
```

---

## Best Practices

### ✅ DO:

1. **Use environment variables for secrets** (S3 keys, DB passwords, API keys)
2. **Add .env to .gitignore** (never commit secrets)
3. **Keep local.json empty or with defaults only** (no secrets!)
4. **Document required env vars** (README, .env.example)
5. **Use custom-environment-variables.json** (standard node-config pattern)
6. **Validate env vars at startup** (fail fast if missing)

### ❌ DON'T:

1. **Hardcode secrets in local.json** (git history risk)
2. **Commit .env files** (use .env.example instead)
3. **Mix template and node-config for same values** (pick one)
4. **Use lowercase env vars** (envsub.awk requires UPPERCASE)
5. **Rely on silent fallbacks** (validate required vars)

---

## References

- **node-config Documentation**: https://github.com/node-config/node-config/wiki/Environment-Variables
- **12-Factor App Config**: https://12factor.net/config
- **ODK Central Docker Setup**: `files/service/scripts/start-odk.sh`
- **VG Fork Config Mapping**: `server/config/custom-environment-variables.json`

---

## Summary

**Stock ODK Central:**
- Uses **template substitution** at container startup
- Simple, explicit, works great for Docker deployments
- Requires container restart for changes

**VG Fork Enhancement:**
- Adds **node-config environment variable mapping**
- Works in Docker AND local development
- Standard pattern, more flexible

**Both approaches coexist** in VG fork for maximum compatibility! 🎯
