# ODK Central Docker Architecture: Deep Technical Analysis

**Updated:** 2026-01-14
**Version:** v2025.4.1
**Purpose:** Comprehensive documentation of container connections, proxying, initialization, and inter-service communication

---

## Executive Summary

ODK Central is a multi-container Docker application with nginx as the central proxy, coordinating requests between:

- **Frontend** (React SPA built into nginx)
- **Backend API** (Node.js/Express "service")
- **Enketo** (form filling engine)
- **PostgreSQL** (data persistence)
- **Redis** (Enketo caching)
- **Pyxform** (XForm conversion)
- **Mail** (email delivery)
- **Secrets** (shared secrets management)

**Key Design Principle:** Nginx is the single entry point, routing all traffic to appropriate services while handling SSL termination, static files, and security.

---

## Container Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │              Docker Network                 │
                    │              (default bridge)              │
                    └─────────────────────────────────────────────┘
                                       │
    ┌──────────────────────────────────┼──────────────────────────────────┐
    │                                  │                                  │
    ▼                                  ▼                                  ▼
┌─────────┐                      ┌─────────┐                      ┌─────────┐
│ Client  │                      │  Nginx  │                      │ Service │
│Browser  │◄─────HTTPS:443──────►│ :443/80 │◄─────HTTP:8383───────►│ :8383   │
└─────────┘                      └─────────┘                      └─────────┘
                                         │                                  │
                    ┌────────────────────┼────────────────────┐              │
                    │                    │                    │              │
                    ▼                    ▼                    ▼              │
              ┌──────────┐         ┌──────────┐         ┌──────────┐        │
              │ Enketo   │         │ Postgres │         │  Pyxform │        │
              │  :8005   │         │  :5432   │         │    :80   │        │
              └──────────┘         └──────────┘         └──────────┘        │
                    │                    │                                  │
                    ▼                    │                                  │
              ┌──────────┐               │                                  │
              │ Redis    │               │                                  │
              │  :6379   │               │                                  │
              │  :6380   │               │                                  │
              └──────────┘               │                                  │
                                         │                                  │
                    ┌────────────────────┼────────────────────┐              │
                    │                    │                    │              ▼
                    ▼                    ▼                    ▼         ┌──────────┐
              ┌──────────┐         ┌──────────┐         ┌──────────┐      │ Secrets │
              │   Mail   │         │ Secrets  │         │ Transfer  │      │ Volume  │
              │   :25    │         │ Volume   │         │   Volume  │      └──────────┘
              └──────────┘         └──────────┘         └──────────┘
```

---

## Container-by-Container Analysis

### 1. Nginx Container (`nginx`)

**Port Exposed:** 80, 443 (host ports configurable via `HTTP_PORT`, `HTTPS_PORT`)

**Dockerfile Build Process:**

```dockerfile
# Stage 1: Build Frontend
FROM node:22.21.1-slim AS intermediate
  └── COPY ./ ./
      └── RUN files/prebuild/write-version.sh
          └── Generates /tmp/version.txt from git describe
      └── RUN files/prebuild/build-frontend.sh
          └── npm ci && npm run build in client/
          └── Output: client/dist/

# Stage 2: Final Nginx Image
FROM ${NGINX_BASE_IMAGE}  # drguptavivek/central-nginx-vg-base:6.0.1 (VG)
  └── Installs netcat-openbsd (for healthcheck)
  └── Creates directories:
      ├── /usr/share/odk/nginx/          # Config templates
      ├── /etc/nginx/modules-enabled/    # Dynamic modules
      ├── /var/log/nginx                 # Logs
      └── /var/log/modsecurity           # WAF logs (VG)
  └── Copies configuration files:
      ├── files/nginx/setup-odk.sh       # ENTRYPOINT script
      ├── files/shared/envsub.awk        # Template processor
      ├── files/nginx/redirector.conf    # HTTP→HTTPS redirect
      ├── files/nginx/backend.conf       # Service proxy config
      ├── files/nginx/common-headers.conf # Security headers
      ├── files/nginx/robots.txt         # SEO/robots
      ├── client/dist/ → /usr/share/nginx/html  # BUILT frontend assets
      └── /tmp/version.txt → /usr/share/nginx/html
```

**Build Context Notes:**
- Add `client/.nginx` to `.dockerignore` to avoid ownership-related Docker build failures when the host directory contains root-owned files.

**What Gets BAKED IN at Build Time:**
1. ✅ Frontend assets (`client/dist/`) - Built React application
2. ✅ Version.txt - Git tag/commit
3. ✅ Nginx configuration templates
4. ✅ Modsecurity module (in base image) - VG
5. ✅ SSL tools (openssl, netcat)

**What Gets GENERATED at Runtime (ENTRYPOINT):**
1. ✅✅ `/etc/nginx/conf.d/odk.conf` - From `odk.conf.template` with env substitution
2. ✅✅ `/usr/share/nginx/html/client-config.json` - Frontend config
3. ✅✅ SSL certificates (self-signed) - If `SSL_TYPE=selfsign`
4. ✅✅ Diffie-Hellman parameters - `/etc/dh/nginx.pem`
5. ✅✅ Letsencrypt certificates - If `SSL_TYPE=letsencrypt`

**ENTRYPOINT: `/scripts/setup-odk.sh`**

```bash
#!/bin/bash
1. Generate client-config.json from template
2. Generate self-signed SSL for invalid.local (catch-all server)
3. Generate DH parameters if needed (2048-bit)
4. Generate self-signed cert for DOMAIN if SSL_TYPE=selfsign
5. Run envsub.awk on templates:
   - redirector.conf → /etc/nginx/conf.d/redirector.conf
   - odk.conf.template → /etc/nginx/conf.d/odk.conf
6. Handle SSL_TYPE:
   - letsencrypt → Start certbot, then nginx
   - upstream → Strip ssl_* directives, listen on :80
   - customssl/selfsign → Start nginx normally
7. exec nginx -g "daemon off;"
```

**Volume Mounts:**
| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./files/local/customssl/` | `/etc/customssl/live/local/:ro` | Custom SSL certificates |
| `./files/nginx/odk.conf.template` | `/usr/share/odk/nginx/odk.conf.template:ro` | Main config template |
| `./files/nginx/client-config.json.template` | `/usr/share/odk/nginx/client-config.json.template:ro` | Frontend config template |
| `./files/vg-nginx/*.conf` (VG) | `/etc/nginx/`, `/usr/share/odk/nginx/` | Modsecurity configs (VG) |

**Environment Variables:**
- `DOMAIN` - Primary domain (e.g., `central.local`)
- `SSL_TYPE` - `letsencrypt`, `selfsign`, `customssl`, `upstream`
- `HTTPS_PORT` - Default 443
- `CERTBOT_EMAIL` - For letsencrypt
- `OIDC_ENABLED` - For SSO
- `SENTRY_ORG_SUBDOMAIN`, `SENTRY_KEY`, `SENTRY_PROJECT` - Error tracking

**Healthcheck:**
```bash
CMD-SHELL, nc -z localhost 80 || exit 1
```

**Nginx Request Flow:**

```
Incoming Request (HTTPS:443)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Server Block: ${DOMAIN} (443 ssl)                           │
├─────────────────────────────────────────────────────────────┤
│ 1. SSL Termination                                          │
│ 2. VG: Modsecurity inspection (WAF)                         │
│ 3. VG: Security headers (vg-headers-more.conf)             │
│ 4. Route by location:                                       │
│                                                              │
│ Location /-/single/* ──────► Redirect to /f/* (Web Forms)   │
│ Location /-/preview/* ─────► Redirect to /f/*/preview       │
│ Location /-/* ──────────────► Proxy to enketo:8005          │
│ Location /v1/* ────────────► Proxy to service:8383 (API)    │
│ Location /oidc/callback ───► Proxy to service:8383 (OIDC)    │
│ Location / ────────────────► Serve frontend SPA             │
│ Location /csp-report ──────► Proxy to Sentry                │
└─────────────────────────────────────────────────────────────┘
```

**Key Nginx Config Sections:**

```nginx
# Default server (catch-all for invalid SNI)
server {
  listen 443 default_server ssl;
  return 421;  # "Misdirected Request" - invalid host
}

# Main server
server {
  listen 443 ssl;
  server_name ${DOMAIN};

  # VG: Modsecurity
  modsecurity on;
  modsecurity_rules_file /etc/modsecurity/modsecurity-odk.conf;

  # VG: Security headers
  include /usr/share/odk/nginx/vg-headers-more.conf;

  # API proxy
  location ~ ^/v\d {
    modsecurity_rules 'SecRuleRemoveById 911100 949110 949111';  # VG
    include /usr/share/odk/nginx/backend.conf;  # proxy_pass http://service:8383
  }

  # Enketo proxy
  location ~ ^/(?:-|enketo-passthrough)(?:/|$) {
    proxy_pass http://enketo:8005;
  }

  # Frontend SPA
  location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
  }
}
```

---

### 2. Service Container (`service`)

**Backend:** Node.js 22.21.1 Express server

**Port Exposed:** 8383 (internal only, not exposed to host)

**Dockerfile Build Process:**

```dockerfile
# Stage 1: Add pgdg repository for PostgreSQL client
FROM node:22.21.1-slim AS pgdg
  └── Install: curl, gpg
  └── Add: apt.postgresql.org repo
  └── Add: PostgreSQL GPG key

# Stage 2: Capture git versions
FROM node:22.21.1-slim AS intermediate
  └── COPY . .
  └── RUN git describe --tags --dirty > /tmp/sentry-versions/central
  └── WORKDIR /server
  └── RUN git describe... > /tmp/sentry-versions/server
  └── WORKDIR /client
  └── RUN git describe... > /tmp/sentry-versions/client

# Stage 3: Final service image
FROM node:22.21.1-slim
  WORKDIR /usr/odk

  # Install system dependencies
  └── Install: gpg, cron, wait-for-it, procps, postgresql-client-14, netcat

  # Install Node dependencies
  COPY server/package*.json ./
  RUN npm clean-install --omit=dev

  # Copy application code
  COPY server/ ./

  # Copy supporting files
  ├── files/shared/envsub.awk → /scripts/
  ├── files/service/scripts/* → ./
  ├── files/service/config.json.template → /usr/share/odk/
  ├── files/service/crontab → /etc/cron.d/odk
  ├── files/service/odk-cmd → /usr/bin/
  └── /tmp/sentry-versions/ → ./
```

**What Gets BAKED IN at Build Time:**
1. ✅ Node.js dependencies (`npm install`)
2. ✅ Application source code (`server/`)
3. ✅ Git version tags (for Sentry)
4. ✅ System utilities (psql, wait-for-it, cron)

**What Gets GENERATED at Runtime:**
1. ✅✅ `config/local.json` - From `config.json.template` with env substitution
2. ✅✅ Database migrations (run at startup)
3. ✅✅ Worker count (based on available memory)

**Command (Entrypoint):**
```bash
wait-for-it ${DB_HOST:-postgres14}:5432 -- ./start-odk.sh
```

**`start-odk.sh` Process:**
```bash
1. Generate config/local.json:
   - Read ENKETO_API_KEY from /etc/secrets/enketo-api-key
   - Compute BASE_URL from DOMAIN and HTTPS_PORT
   - Run envsub.awk on config.json.template

2. Set up Sentry:
   - SENTRY_RELEASE from sentry-versions/server
   - SENTRY_TAGS with central/client versions

3. Run database migrations:
   - node ./lib/bin/run-migrations

4. Log server upgrade:
   - node ./lib/bin/log-upgrade

5. Start cron daemon:
   - cron -f &

6. Determine worker count:
   - Get cgroup memory limit
   - If >1.1GB → 4 workers, else 1 worker

7. Start PM2:
   - exec npx pm2-runtime ./pm2.config.js
```

**Volume Mounts:**
| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `secrets` (named volume) | `/etc/secrets` | Shared secrets (enketo keys) |
| `/data/transfer` (bind mount) | `/data/transfer` | OData/S3 blob transfer |

**Environment Variables (Database):**
- `DB_HOST=postgres14` - PostgreSQL host
- `DB_USER=odk` - Database user
- `DB_PASSWORD=odk` - Database password
- `DB_NAME=odk` - Database name
- `DB_POOL_SIZE=10` - Connection pool size
- `DB_SSL=null` - SSL for DB connection

**Environment Variables (Email):**
- `EMAIL_FROM=no-reply@$DOMAIN`
- `EMAIL_HOST=mail`
- `EMAIL_PORT=25`
- `EMAIL_SECURE=false`
- `EMAIL_IGNORE_TLS=true`
- `EMAIL_USER=`
- `EMAIL_PASSWORD=`

**Environment Variables (Enketo):**
- Computed from `BASE_URL` and secrets volume

**Environment Variables (OIDC):**
- `OIDC_ENABLED=false`
- `OIDC_ISSUER_URL=`
- `OIDC_CLIENT_ID=`
- `OIDC_CLIENT_SECRET=`

**Environment Variables (S3 - Optional):**
- `S3_SERVER=`
- `S3_ACCESS_KEY=`
- `S3_SECRET_KEY=`
- `S3_BUCKET_NAME=`

**Environment Variables (Other):**
- `DOMAIN`, `SYSADMIN_EMAIL`, `HTTPS_PORT`
- `SENTRY_*` - Error tracking
- `SESSION_LIFETIME=86400` - 24 hours

**Dependencies (`depends_on`):**
- `secrets` - Must exist first
- `postgres14` - Database must be ready
- `mail` - Email service
- `pyxform` - Form conversion
- `enketo` - Form filling

**PM2 Configuration:**
- Runs 1-4 workers (based on memory)
- Cluster mode
- Auto-restart on failure
- Zero-downtime reloads

**Cron Jobs (`/etc/cron.d/odk`):**
```
# Background task processing
*/5 * * * * cd /usr/odk && node ./lib/bin/process-backlog
*/5 * * * * cd /usr/odk && node ./lib/bin/upload-blobs
*/5 * * * * cd /usr/odk && node ./lib/bin/reap-sessions
0 3 * * * cd /usr/odk && node ./lib/bin/purge
0 4 * * * cd /usr/odk && node ./lib/bin/run-analytics
```

---

### 3. Enketo Container (`enketo`)

**Purpose:** Form filling engine (offline-capable web forms)

**Port Exposed:** 8005 (internal only, or `8005:8005` in dev)

**Dockerfile:**
```dockerfile
FROM ghcr.io/enketo/enketo:7.5.1

ENV ENKETO_SRC_DIR=/srv/src/enketo/packages/enketo-express
WORKDIR ${ENKETO_SRC_DIR}

COPY files/shared/envsub.awk /scripts/
COPY files/enketo/config.json.template → config/config.json.template
COPY files/enketo/config.json.template → config/config.json (for client build)
COPY files/enketo/start-enketo.sh → start-enketo.sh

EXPOSE 8005
CMD ["./start-enketo.sh"]
```

**What Gets BAKED IN:**
1. ✅ Enketo source code (from upstream image)
2. ✅ Configuration templates

**What Gets GENERATED at Runtime:**
1. ✅✅ `config/config.json` - Templated with secrets

**`start-enketo.sh` Process:**
```bash
1. Check secrets exist:
   - /etc/secrets/enketo-secret (64 bytes)
   - /etc/secrets/enketo-less-secret (32 bytes)
   - /etc/secrets/enketo-api-key (128 bytes)

2. Generate config:
   SECRET=$(cat /etc/secrets/enketo-secret)
   LESS_SECRET=$(cat /etc/secrets/enketo-less-secret)
   API_KEY=$(cat /etc/secrets/enketo-api-key)
   BASE_URL=$(https://${DOMAIN} or ${DOMAIN}:${HTTPS_PORT})

   Run envsub.awk on config.json.template

3. Start Enketo:
   exec yarn workspace enketo-express start
```

**Volume Mounts:**
- `secrets:/etc/secrets` - Shared secrets

**Environment Variables:**
- `DOMAIN` - For API communication
- `SUPPORT_EMAIL` - For support link
- `HTTPS_PORT` - For generating URLs
- `ENV=DEV` (dev only)
- `ENKETO_SECRETS=danger-insecure` (dev only)
- `NODE_TLS_REJECT_UNAUTHORIZED=0` (dev only)

**Dependencies:**
- `secrets` - Must generate secrets first
- `enketo_redis_main` - Main data store
- `enketo_redis_cache` - Caching layer

**Redis Configuration:**
```javascript
"redis": {
  "main": {
    "host": "enketo_redis_main",
    "port": "6379"
  },
  "cache": {
    "host": "enketo_redis_cache",
    "port": "6380"
  }
}
```

**Communication with Service:**
- Enketo → Service: Via API key authentication
- Service → Enketo: HTTP requests to `http://enketo:8005/-`
- Shared secret: `/etc/secrets/enketo-api-key`

---

### 4. Secrets Container (`secrets`)

**Purpose:** Generate and store shared secrets

**Dockerfile:**
```dockerfile
FROM node:22.21.1-slim
COPY files/enketo/generate-secrets.sh ./
CMD ["./generate-secrets.sh"]
```

**`generate-secrets.sh`:**
```bash
#!/bin/bash
if [ ! -f /etc/secrets/enketo-secret ]; then
  head -c1024 /dev/urandom | LC_ALL=C tr -dc '[:alnum:]' | head -c64 > /etc/secrets/enketo-secret
fi

if [ ! -f /etc/secrets/enketo-less-secret ]; then
  head -c512 /dev/urandom | LC_ALL=C tr -dc '[:alnum:]' | head -c32 > /etc/secrets/enketo-less-secret
fi

if [ ! -f /etc/secrets/enketo-api-key ]; then
  head -c2048 /dev/urandom | LC_ALL=C tr -dc '[:alnum:]' | head -c128 > /etc/secrets/enketo-api-key
fi
```

**What Gets GENERATED (one-time):**
1. ✅ `/etc/secrets/enketo-secret` - 64 chars (main encryption key)
2. ✅ `/etc/secrets/enketo-less-secret` - 32 chars (less secure operations)
3. ✅ `/etc/secrets/enketo-api-key` - 128 chars (API authentication)

**Volume Mounts:**
- `secrets:/etc/secrets` - Named volume for persistence

**Lifecycle:**
1. Container starts
2. Generates secrets if they don't exist
3. Container exits (one-time job)
4. Secrets persist in named volume
5. Other containers mount the same volume

**Dev Mode Secrets:**
- **docker-compose.vg-dev.yml**: Profile management (separate) and HMR dev overrides

### Usage
```bash
# Production (with modsecurity security)
docker compose up

# Development (with modsecurity + dev tools)
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml up -d
```

### Dev Mode Secrets:
In dev (`docker-compose.vg-dev.yml`), secrets are pre-generated:

### Development Mode

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml up -d
```

**Differences:**
1. **Exposed ports:**
   - Postgres14: `5432:5432` (direct access)
   - Pyxform: `5001:80` (direct access)
   - Enketo: `8005:8005` (direct access)
   - Redis: `63799:6379`, `63800:6380` (direct access)
3. **Skip frontend build:**
   - `SKIP_FRONTEND_BUILD=1` nginx build arg

4. **Mail disabled:**
   - `profiles: none` for mail

5. **Enketo dev mode:**
   - `ENV=DEV`
   - `ENKETO_SECRETS=danger-insecure`
   - `NODE_TLS_REJECT_UNAUTHORIZED=0`

---

## VG-Specific Additions

### Modsecurity Integration (VG)

**Additional Components:**
1. **Custom Nginx Base Image:** `drguptavivek/central-nginx-vg-base:6.0.1`
   - Compiled with Modsecurity v3.x
   - OWASP CRS support

2. **Volume Mounts:**
   - `./files/vg-nginx/vg-nginx-modules.conf` - Module loading
   - `./files/vg-nginx/vg-modsecurity-odk.conf` - WAF config
   - `./files/vg-nginx/vg-headers-more.conf` - Security headers
   - `./crs/` - OWASP CRS v4.21.0 rules
   - `./crs_custom/` - Custom CRS exclusions
   - `./logs/nginx/` - Nginx logs
   - `./logs/modsecurity/` - WAF audit logs

3. **Nginx Config Additions:**
   ```nginx
   # Global modsecurity enable
   modsecurity on;
   modsecurity_rules_file /etc/modsecurity/modsecurity-odk.conf;

   # Security headers
   include /usr/share/odk/nginx/vg-headers-more.conf;

   # API endpoint exclusions
   location ~ ^/v\d {
     modsecurity_rules 'SecRuleRemoveById 911100 949110 949111';
   }
   ```

---

## Security Considerations

### Network Isolation

- ✅ All services on internal Docker network
- ✅ Only nginx exposes ports to host
- ✅ Inter-service communication via DNS
- ✅ No inter-container TLS (trusted network)

### Secrets Management

- ✅ Secrets stored in named volume
- ✅ Generated once, persisted across restarts
- ✅ Shared between service and enketo
- ✅ API key authentication for enketo

### SSL/TLS

- ✅ SSL termination at nginx
- ✅ Multiple SSL modes: letsencrypt, selfsign, customssl, upstream
- ✅ HSTS headers
- ✅ Secure cipher suites

### Web Application Firewall (VG)

- ✅ Modsecurity with OWASP CRS
- ✅ Request inspection before backend
- ✅ Configured exclusions for API endpoints
- ✅ JSON audit logging

---

## Performance Considerations

### Caching Strategy

Nginx cache strategy map:
```nginx
$cache_strategy:
  /assets/* → immutable (1 year)
  /v1/* → passthrough (no caching)
  /client-config.json → revalidate (no-cache)
  /-/* → revalidate or immutable depending on file
```

### Database Connection Pool

- Service maintains 10 connections to Postgres
- PM2 runs 1-4 workers (memory-dependent)
- Each worker has its own connection pool

### Redis Caching

- Enketo uses two Redis instances
- Main: Persistent data storage
- Cache: Performance optimization

---

## Troubleshooting

### Common Issues

**Service won't start:**
1. Check if postgres14 is ready: `docker compose logs postgres14`
2. Check if secrets exist: `docker compose exec secrets ls /etc/secrets`
3. Check service logs: `docker compose logs service`

**Nginx 502 Bad Gateway:**
1. Service not ready? Wait for migrations
2. Wrong port? Check service is on :8383
3. DNS issue? `docker compose exec nginx ping service`

**Enketo not working:**
1. Check secrets exist: `docker compose exec enketo ls /etc/secrets`
2. Check Redis: `docker compose logs enketo_redis_main`
3. Check API key matches service

**Database connection failed:**
1. Check postgres14: `docker compose ps postgres14`
2. Check network: `docker compose exec service ping postgres14`
3. Check credentials in environment

### Debugging Commands

```bash
# Check all containers
docker compose ps

# Check specific service logs
docker compose logs service -f --tail=50

# Enter container shell
docker compose exec service bash
docker compose exec nginx sh

# Check inter-container communication
docker compose exec service ping postgres14
docker compose exec service curl http://service:8383

# Check secrets
docker compose exec service cat /etc/secrets/enketo-api-key

# Check nginx config
docker compose exec nginx nginx -t

# Check database connection
docker compose exec service psql -U odk -d odk -c "SELECT 1"

# Check Redis
docker compose exec enketo_redis_main redis-cli ping
```

---

## Summary

**Key Architectural Decisions:**

1. **Nginx as central proxy** - Single entry point, SSL termination, routing
2. **Secrets container** - One-time secret generation, shared via volume
3. **Frontend baked in** - No separate frontend container in production
4. **Service as orchestrator** - Coordinates all background tasks via cron
5. **Enketo as separate service** - Form filling engine with Redis backend
6. **Modsecurity (VG)** - WAF protection at nginx level

**What Happens When:**

- **`docker compose build`:**
  - Frontend built (`npm run build`)
  - Nginx image created with frontend assets
  - Service image created with dependencies
  - Enketo image pulled from upstream

- **`docker compose up`:**
  - Secrets generated (one-time)
  - Databases initialized
  - Migrations run
  - All services started
  - Nginx proxies configured

- **`docker compose down`:**
  - All containers stopped
  - Named volumes persist (data saved)
  - Anonymous volumes removed

- **`docker compose down -v`:**
  - All containers stopped
  - All volumes removed (data lost!)

---

**For VG-specific modifications, see:** `docs/vg/vg-core-central-edits.md`
