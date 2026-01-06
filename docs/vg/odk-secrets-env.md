# ODK Central Secrets and Environment Variables

**Based on upstream getodk/central master branch**

---

## Overview

ODK Central uses two distinct secret management approaches:

1. **Auto-generated Enketo secrets** (persisted in docker volume, generated once)
2. **Environment-based configuration** (templated from .env at runtime)

---

## Secret Types

| Secret Type | Source | When Generated | Persistence | Rebuild Required | Restart Required |
|-------------|--------|----------------|-------------|------------------|------------------|
| **Enketo API secrets** | Auto-generated | First container run | Docker volume `secrets` | ❌ No | ❌ No |
| **Database credentials** | `.env` | Runtime templating | Environment variables | ❌ No | ✅ Yes |
| **S3 credentials** | `.env` | Runtime templating | Environment variables | ❌ No | ✅ Yes |
| **Email credentials** | `.env` | Runtime templating | Environment variables | ❌ No | ✅ Yes |
| **SSL certificates** | Auto-generated or user-provided | Container start | Docker volume or bind mount | ❌ No | Varies |
| **OIDC secrets** | `.env` | Runtime templating | Environment variables | ❌ No | ✅ Yes |

---

## 1. Enketo Auto-Generated Secrets

### Generation Process

**Container:** `secrets`
**Script:** `files/enketo/generate-secrets.sh`
**Dockerfile:** `secrets.dockerfile`

```dockerfile
FROM node:22.21.1-slim
COPY files/enketo/generate-secrets.sh ./
```

```yaml
# docker-compose.yml
secrets:
  volumes:
    - secrets:/etc/secrets
  build:
    context: .
    dockerfile: secrets.dockerfile
  command: './generate-secrets.sh'
```

**Script logic:**
```bash
# Only generates if files don't exist
if [ ! -f /etc/secrets/enketo-secret ]; then
  head -c1024 /dev/urandom | LC_ALL=C tr -dc '[:alnum:]' | head -c64  > /etc/secrets/enketo-secret
fi

if [ ! -f /etc/secrets/enketo-less-secret ]; then
  head -c512  /dev/urandom | LC_ALL=C tr -dc '[:alnum:]' | head -c32  > /etc/secrets/enketo-less-secret
fi

if [ ! -f /etc/secrets/enketo-api-key ]; then
  head -c2048 /dev/urandom | LC_ALL=C tr -dc '[:alnum:]' | head -c128 > /etc/secrets/enketo-api-key
fi
```

### Generated Files

| File | Size | Purpose |
|------|------|---------|
| `/etc/secrets/enketo-secret` | 64 bytes | Enketo encryption key |
| `/etc/secrets/enketo-less-secret` | 32 bytes | Enketo less-secure encryption key |
| `/etc/secrets/enketo-api-key` | 128 bytes | API key for Service ↔ Enketo communication |

### Persistence

- **Volume:** `secrets` (named docker volume)
- **Shared by:** `secrets`, `service`, `enketo` containers
- **Lifecycle:** Generated once on first run, persists across container restarts/rebuilds
- **Regeneration:** Only if volume is deleted (`docker volume rm central_secrets`)

---

## 2. Runtime Configuration Templating

### Service Container (`service`)

**When:** Every container start (via `start-odk.sh`)
**Template:** `/usr/share/odk/config.json.template`
**Output:** `/usr/odk/config/local.json`

```bash
# files/service/scripts/start-odk.sh
ENKETO_API_KEY=$(cat /etc/secrets/enketo-api-key) \
BASE_URL=$( [ "${HTTPS_PORT}" = 443 ] && echo https://"${DOMAIN}" || echo https://"${DOMAIN}":"${HTTPS_PORT}" ) \
/scripts/envsub.awk \
    < /usr/share/odk/config.json.template \
    > /usr/odk/config/local.json
```

**Template variables (from .env):**
```json
{
  "database": {
    "host": "${DB_HOST}",
    "user": "${DB_USER}",
    "password": "${DB_PASSWORD}",
    "database": "${DB_NAME}",
    "ssl": ${DB_SSL}
  },
  "email": {
    "transportOpts": {
      "auth": {
        "user": "${EMAIL_USER}",
        "pass": "${EMAIL_PASSWORD}"
      }
    }
  },
  "enketo": {
    "apiKey": "${ENKETO_API_KEY}"
  },
  "external": {
    "s3blobStore": {
      "server": "${S3_SERVER}",
      "accessKey": "${S3_ACCESS_KEY}",
      "secretKey": "${S3_SECRET_KEY}",
      "bucketName": "${S3_BUCKET_NAME}"
    }
  }
}
```

### Enketo Container (`enketo`)

**When:** Every container start (via `start-enketo.sh`)
**Template:** `${ENKETO_SRC_DIR}/config/config.json.template`
**Output:** `${ENKETO_SRC_DIR}/config/config.json`

```bash
# files/enketo/start-enketo.sh
BASE_URL=$( [ "${HTTPS_PORT}" = 443 ] && echo https://"${DOMAIN}" || echo https://"${DOMAIN}":"${HTTPS_PORT}" ) \
SECRET=$(cat /etc/secrets/enketo-secret) \
LESS_SECRET=$(cat /etc/secrets/enketo-less-secret) \
API_KEY=$(cat /etc/secrets/enketo-api-key) \
/scripts/envsub.awk \
    < "$CONFIG_PATH.template" \
    > "$CONFIG_PATH"
```

**Template variables:**
```json
{
  "encryption key": "${SECRET}",
  "less secure encryption key": "${LESS_SECRET}",
  "linked form and data server": {
    "api key": "${API_KEY}",
    "server url": "${DOMAIN}"
  }
}
```

### Nginx Container (`nginx`)

**When:** Every container start (via `setup-odk.sh`)
**Template:** `/usr/share/odk/nginx/client-config.json.template`
**Output:** `/usr/share/nginx/html/client-config.json`

```bash
# files/nginx/setup-odk.sh
/scripts/envsub.awk \
  < /usr/share/odk/nginx/client-config.json.template \
  > /usr/share/nginx/html/client-config.json
```

**Template variables:**
```json
{
  "oidcEnabled": ${OIDC_ENABLED}
}
```

---

## 3. Environment Variable Passing

### docker-compose.yml Pattern

```yaml
service:
  environment:
    - DOMAIN=${DOMAIN}
    - DB_HOST=${DB_HOST:-postgres14}
    - DB_USER=${DB_USER:-odk}
    - DB_PASSWORD=${DB_PASSWORD:-odk}
    - DB_NAME=${DB_NAME:-odk}
    - DB_SSL=${DB_SSL:-null}
    - S3_SERVER=${S3_SERVER:-}
    - S3_ACCESS_KEY=${S3_ACCESS_KEY:-}
    - S3_SECRET_KEY=${S3_SECRET_KEY:-}
    - S3_BUCKET_NAME=${S3_BUCKET_NAME:-}
    - EMAIL_USER=${EMAIL_USER:-}
    - EMAIL_PASSWORD=${EMAIL_PASSWORD:-}
```

**Pattern:** `${VAR:-default}`
- If `VAR` is set in `.env` → use that value
- If `VAR` is unset or empty → use `default`
- If `VAR` has no default → empty string

---

## 4. Impact of Changing .env

| Change Type | Image Rebuild | Container Restart | Effect |
|-------------|---------------|-------------------|--------|
| **Change NGINX_BASE_IMAGE** | ✅ Yes | ✅ Yes (nginx) | New base image with different modules (e.g., ModSecurity) |
| **Change DOMAIN** | ❌ No | ✅ Yes (all) | Config regenerated at runtime |
| **Change DB credentials** | ❌ No | ✅ Yes (service) | New config.json at startup |
| **Change S3 credentials** | ❌ No | ✅ Yes (service) | New config.json at startup |
| **Change EMAIL credentials** | ❌ No | ✅ Yes (service) | New config.json at startup |
| **Change SSL_TYPE** | ❌ No | ✅ Yes (nginx) | New SSL setup at startup |
| **Change HTTPS_PORT** | ❌ No | ✅ Yes (all) | URLs regenerated at startup |
| **Change OIDC_ENABLED** | ❌ No | ✅ Yes (nginx, service) | Client config regenerated |

**Key Rule:** Most `.env` changes require container restart only. **NGINX_BASE_IMAGE is the exception**—it requires image rebuild because it's a build-time ARG in the dockerfile.

---

## 5. Secrets Lifecycle Examples

### Scenario 1: Fresh Installation

```bash
# Step 1: Configure .env
cp .env.template .env
vim .env  # Set DOMAIN, SYSADMIN_EMAIL, DB_PASSWORD, S3_ACCESS_KEY, etc.

# Step 2: Start stack
docker compose up -d

# What happens:
# 1. secrets container runs generate-secrets.sh → creates 3 files in 'secrets' volume
# 2. service container starts → reads enketo-api-key, templates config.json using .env
# 3. enketo container starts → reads all 3 secrets, templates config.json using .env
# 4. nginx container starts → templates client-config.json using .env

# Result:
# - Enketo secrets: Auto-generated, persist in volume
# - All other secrets: From .env, templated at runtime
```

### Scenario 2: Change Database Password

```bash
# Step 1: Update .env
vim .env  # Change DB_PASSWORD=newpassword

# Step 2: Restart service
docker compose restart service

# What happens:
# - service reads new DB_PASSWORD from environment
# - start-odk.sh templates new config.json with new password
# - Migrations run with new credentials
# - Server starts with new DB connection

# Enketo secrets: Unchanged (not affected)
# Image rebuild: NOT required
```

### Scenario 3: Rotate S3 Credentials

```bash
# Step 1: Generate new S3 keys externally (e.g., in AWS/Garage)

# Step 2: Update .env
vim .env  # Change S3_ACCESS_KEY and S3_SECRET_KEY

# Step 3: Restart service
docker compose restart service

# What happens:
# - service reads new S3 credentials from environment
# - start-odk.sh templates new config.json with new keys
# - S3 client reinitializes with new credentials

# Enketo secrets: Unchanged
# Image rebuild: NOT required
```

### Scenario 4: Rotate Enketo Secrets (Advanced)

```bash
# WARNING: This breaks existing Enketo sessions

# Step 1: Stop all containers
docker compose down

# Step 2: Delete secrets volume
docker volume rm central_secrets

# Step 3: Restart stack
docker compose up -d

# What happens:
# - secrets container recreates all 3 files with NEW random values
# - service reads new enketo-api-key
# - enketo reads new encryption keys
# - All previous Enketo sessions/cookies invalidated

# Use case: Security incident, key compromise
```

### Scenario 5: Change Domain

```bash
# Step 1: Update DNS (external)
# Point new-domain.com → server IP

# Step 2: Update .env
vim .env  # Change DOMAIN=new-domain.com

# Step 3: Restart affected containers
docker compose restart service enketo nginx

# What happens:
# - service: BASE_URL regenerated in config.json
# - enketo: server_url regenerated in config.json
# - nginx: client-config.json regenerated, SSL setup rerun

# If SSL_TYPE=letsencrypt:
# - New certificate requested for new domain

# Enketo secrets: Unchanged (persist)
# Image rebuild: NOT required
```

---

## 6. Security Best Practices

### .env File Protection

```bash
# Never commit .env to git
echo ".env" >> .gitignore

# Restrict permissions
chmod 600 .env
chown root:root .env

# Backup encrypted
gpg --encrypt .env > .env.gpg
```

### Secrets Volume Backup

```bash
# Backup Enketo secrets (for disaster recovery)
docker run --rm -v central_secrets:/secrets -v $(pwd):/backup alpine tar czf /backup/enketo-secrets.tar.gz -C /secrets .

# Restore Enketo secrets
docker run --rm -v central_secrets:/secrets -v $(pwd):/backup alpine tar xzf /backup/enketo-secrets.tar.gz -C /secrets
```

### Credential Rotation Schedule

| Credential | Rotation Frequency | Method |
|------------|-------------------|--------|
| **Enketo secrets** | Only on compromise | Delete volume + restart |
| **Database password** | Yearly | Update .env + restart service |
| **S3 credentials** | Quarterly | Update .env + restart service |
| **Email password** | Yearly | Update .env + restart service |
| **OIDC client secret** | Per provider policy | Update .env + restart service/nginx |

---

## 7. Troubleshooting

### Issue: Service can't connect to database

```bash
# Check if DB_PASSWORD in .env matches postgres container
docker compose exec postgres14 psql -U odk -c "SELECT 1"

# Verify config.json has correct credentials
docker compose exec service cat /usr/odk/config/local.json | grep -A 5 database
```

### Issue: Enketo forms fail to load

```bash
# Check if enketo-api-key matches between service and enketo
docker compose exec service cat /usr/odk/config/local.json | grep apiKey
docker compose exec enketo cat /srv/src/enketo/packages/enketo-express/config/config.json | grep "api key"

# Verify secrets exist and have correct size
docker compose exec enketo ls -lh /etc/secrets/
# Should show:
# -rw-r--r-- 1 node node  64 Jan  6 10:00 enketo-secret
# -rw-r--r-- 1 node node  32 Jan  6 10:00 enketo-less-secret
# -rw-r--r-- 1 node node 128 Jan  6 10:00 enketo-api-key
```

### Issue: S3 uploads fail after credential rotation

```bash
# Verify new credentials are in environment
docker compose exec service env | grep S3_

# Verify config.json was regenerated
docker compose exec service cat /usr/odk/config/local.json | grep -A 8 s3blobStore

# Test S3 connection manually
docker compose exec service node -e "
const config = require('./config/local.json');
console.log('S3 Config:', config.default.external.s3blobStore);
"
```

### Issue: .env changes not taking effect

```bash
# Common mistake: Edited .env but didn't restart
docker compose restart service

# Verify environment variables are passed correctly
docker compose config | grep -A 20 "service:" | grep environment

# Check what service container sees
docker compose exec service env | sort
```

---

## 8. Build Time vs Runtime

### Build Time (Image Creation)

**What's included in image:**
- Application code (server/, client/)
- Template files (*.template)
- Scripts (start-odk.sh, generate-secrets.sh, envsub.awk)
- Nginx static content (HTML, CSS, JS)

**What's NOT in image:**
- Secrets (Enketo or otherwise)
- .env values
- Generated configuration files (config.json, client-config.json)
- SSL certificates

**Implications:**
- Images are safe to share (no secrets baked in)
- Same image works across dev/staging/prod (configuration at runtime)
- Can push to Docker Hub without leaking credentials

### Runtime (Container Start)

**What happens on container start:**
1. **secrets container:** Generates Enketo secrets if missing
2. **service container:**
   - Reads Enketo API key from volume
   - Reads all other config from environment variables
   - Templates `/usr/odk/config/local.json`
   - Runs migrations
   - Starts server
3. **enketo container:**
   - Reads all 3 secrets from volume
   - Reads DOMAIN/HTTPS_PORT from environment
   - Templates config.json
   - Starts Enketo server
4. **nginx container:**
   - Reads OIDC_ENABLED from environment
   - Templates client-config.json
   - Generates/loads SSL certificates
   - Starts nginx

**Implications:**
- Configuration changes require restart, not rebuild
- Different environments use same images, different .env
- Secrets are runtime-injected, never build-time

---

## 9. Configuration File Locations

| Container | Template Location | Output Location | Templating Tool |
|-----------|------------------|-----------------|-----------------|
| **service** | `/usr/share/odk/config.json.template` | `/usr/odk/config/local.json` | `envsub.awk` |
| **enketo** | `${ENKETO_SRC_DIR}/config/config.json.template` | `${ENKETO_SRC_DIR}/config/config.json` | `envsub.awk` |
| **nginx** | `/usr/share/odk/nginx/client-config.json.template` | `/usr/share/nginx/html/client-config.json` | `envsub.awk` |
| **nginx** | `/usr/share/odk/nginx/odk.conf.template` | `/etc/nginx/conf.d/odk.conf` | `envsub.awk` |

---

## 10. Summary Decision Matrix

**Question:** Do I need to rebuild the image?

| Change | Rebuild? | Restart? | Why |
|--------|----------|----------|-----|
| Change S3_ACCESS_KEY, S3_SECRET_KEY | ❌ No | ✅ Yes | Runtime templating in config.json |
| Change DB_PASSWORD | ❌ No | ✅ Yes | Runtime templating in config.json |
| Change DOMAIN | ❌ No | ✅ Yes | Runtime templating in config.json |
| Change NGINX_BASE_IMAGE | ✅ Yes | ✅ Yes | Build-time ARG in dockerfile |
| Change SSL_TYPE | ❌ No | ✅ Yes | Runtime SSL setup in nginx |
| Change application code | ✅ Yes | ✅ Yes | Code copied into image |
| Rotate Enketo secrets | ❌ No | ✅ Yes (after volume delete) | Volume management |
| Upgrade Node.js/base image | ✅ Yes | ✅ Yes | Base image change |

**Golden Rule:** If it's a build-time ARG (like NGINX_BASE_IMAGE), rebuild is required. For most other .env variables, restart is enough due to runtime templating.

---

**End of Document**
