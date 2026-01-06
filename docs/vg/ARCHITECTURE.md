# ODK Central VG Fork - Architecture and Configuration

## Overview

This document explains the architecture of ODK Central VG fork and how configuration flows through the system.

---

## The 4 Decision Points

All configuration derives from **4 key decisions**:

```
┌─────────────────────────────────────────┐
│ 1. Environment: Dev | Prod              │
│ 2. S3 Storage: None | Garage | External │
│ 3. Database: Container | Local | Hosted │
│ 4. SSL: selfsign | LE | customssl | up  │
└──────────────────────────────────────────┘
         + DOMAIN + EMAIL
                 │
                 ▼
     ┌──────────────────────┐
     │ Auto-Derive Config:  │
     │ - Ports (80/8080)    │
     │ - S3_SERVER URL      │
     │ - DB connection      │
     │ - SSL certificates   │
     │ - nginx routing      │
     └──────────────────────┘
                 │
                 ▼
          .env file (complete)
                 │
                 ▼
     ┌──────────────────────┐
     │ docker-compose up -d │
     │ (all 12 services)    │
     └──────────────────────┘
```

---

## Service Architecture

### 12 Core Services

```
┌──────────────────────────────────────────────────────────────────┐
│                    External Clients                              │
│          (ODK Collect, Web Browsers, S3 downloads)               │
└────────────────────┬─────────────────────────────────────────────┘
                     │ HTTPS (443 or custom)
                     │
        ┌────────────▼──────────────┐
        │  nginx (SSL termination)  │
        │  - ModSecurity WAF        │
        │  - Routes by Host header  │
        │  - Proxies to services    │
        └────────┬────────┬─────────┘
                 │        │
        ╔════════╧════╗  ╔╧═════════════╗
        ║ Main domain ║  ║ S3 subdomains║
        ║ (service)   ║  ║ (garage)     ║
        ╚════════╤════╝  ╚╤═════════════╝
                 │        │
        ┌────────▼──────┐ │
        │  service:8383 │ │  ┌─────────────────┐
        │  - API        │ │  │  garage:3900    │
        │  - Auth       │ │  │  - S3 API       │
        │  - Telemetry  │ │  │  - Virtual-host │
        └────┬──────────┘ │  └─────────────────┘
             │            │
   ┌─────────┴────┬───────┤
   │              │       └──────────────┬──────────────┐
   │              │                      │              │
┌──▼──┐  ┌───────▼───┐  ┌───────────┐   │   ┌─────────▼──┐
│ DB  │  │  Enketo   │  │ pyxform   │   │   │ Redis caches
│     │  │  :8005    │  │ :80       │   │   │ :6379, 6380
└─────┘  └────┬──────┘  └───────────┘   │   └────────────┘
              │                          │
       ┌──────▼─────────┐                │
       │  Redis caches  │                │
       │  (main, cache) │                │
       └────────────────┘
                                    [Optional: External DB, RDS, etc.]
                                    [Optional: External S3, AWS, etc.]
```

### Services and Ports

| Service | Internal | Host | Protocol | Purpose |
|---------|----------|------|----------|---------|
| **nginx** | n/a | 80,443 (or 8080,8443) | HTTP/HTTPS | Reverse proxy, SSL, ModSecurity WAF |
| **service** | 8383 | internal | HTTP | ODK backend API, auth, telemetry |
| **postgres14** | 5432 | internal | TCP | PostgreSQL database |
| **enketo** | 8005 | internal | HTTP | Form rendering engine |
| **enketo_redis_main** | 6379 | internal | TCP | Redis (main forms) |
| **enketo_redis_cache** | 6380 | internal | TCP | Redis (cache) |
| **pyxform** | 80 | internal | HTTP | XForm conversion |
| **mail** | 25 | internal | SMTP | Email delivery |
| **secrets** | n/a | internal | - | Generates Enketo keys |
| **garage** | 3900,3903 | 127.0.0.1 | HTTP | S3 API and Web UI |

---

## Configuration Flow

### 1. User Configuration (via init-odk.sh)

```
User answers 4 questions
        ↓
init-odk.sh
        ↓
Derives all other config
        ↓
Generates .env file
```

### 2. Environment Variables (.env → docker-compose.yml)

**Build time (image creation):**
- `NGINX_BASE_IMAGE`: Baked into nginx image as ARG (requires rebuild if changed)

**Runtime (container start):**
- All other variables: Passed to containers, templated at startup

```yaml
# docker-compose.yml
service:
  environment:
    - DOMAIN=${DOMAIN}                    # From .env
    - DB_HOST=${DB_HOST:-postgres14}      # From .env or default
    - S3_SERVER=${S3_SERVER:-}            # Optional
    - HTTPS_PORT=${HTTPS_PORT:-443}       # From .env or default
    # ... 20+ variables
```

### 3. Runtime Configuration (Templating)

**When containers start:**

```
.env variables
    ↓
[Container Start Script: start-odk.sh, start-enketo.sh, setup-odk.sh]
    ↓
envsub.awk (template processor)
    ↓
Template files (*.template)
    ↓
Generated config files:
  - service: /usr/odk/config/local.json
  - enketo: config/config.json
  - nginx: /etc/nginx/conf.d/odk.conf
  - client: /usr/share/nginx/html/client-config.json
```

### 4. Service Startup Order

**Docker-compose dependencies ensure order:**

```
1. postgres14 (database)
2. mail (email, slow to start)
3. secrets (generate Enketo keys)
4. pyxform (XForm converter)
5. enketo_redis_main, enketo_redis_cache
6. enketo (needs redis)
7. garage (S3 storage, if enabled)
8. service (needs postgres, enketo, secrets, pyxform, garage)
9. nginx (needs service)
```

---

## Configuration Examples

### Example 1: Dev Setup (Minimal)

**User answers:**
```
1. Dev
2. None (blobs in PostgreSQL)
3. Container (postgres14)
4. selfsign
Domain: central.local
```

**Auto-derived:**
```bash
DOMAIN=central.local
SSL_TYPE=selfsign
HTTP_PORT=80
HTTPS_PORT=443
DB_HOST=postgres14
DB_USER=odk
DB_PASSWORD=odk
DB_NAME=odk
DB_SSL=null
S3_SERVER=        # Empty - no S3
```

**What starts:**
- postgres14, secrets, enketo, pyxform, mail, service, nginx
- No garage (S3 disabled)

**nginx routing:**
```nginx
server {
  listen 443 ssl;
  server_name central.local;
  proxy_pass http://service:8383;
}
```

### Example 2: Prod with Garage

**User answers:**
```
1. Prod
2. Local Garage
3. Container
4. letsencrypt
Domain: central.yourdomain.com
```

**Auto-derived:**
```bash
DOMAIN=central.yourdomain.com
SSL_TYPE=letsencrypt
HTTP_PORT=80
HTTPS_PORT=443
S3_SERVER=https://odk-central.s3.central.yourdomain.com
S3_BUCKET_NAME=odk-central
S3_ACCESS_KEY=<generated>
S3_SECRET_KEY=<generated>
EXTRA_SERVER_NAME=odk-central.s3.central.yourdomain.com web.central.yourdomain.com
```

**What starts:**
- All services including garage

**nginx routing:**
```nginx
server {
  listen 443 ssl;
  server_name central.yourdomain.com;
  proxy_pass http://service:8383;
}

server {
  listen 443 ssl;
  server_name odk-central.s3.central.yourdomain.com s3.central.yourdomain.com;
  proxy_pass http://garage:3900;
}

server {
  listen 443 ssl;
  server_name web.central.yourdomain.com;
  proxy_pass http://garage:3903;
}
```

**Let's Encrypt certificate:**
- Covers: central.yourdomain.com, odk-central.s3.central.yourdomain.com, web.central.yourdomain.com

### Example 3: Prod with External S3 and RDS

**User answers:**
```
1. Prod
2. External S3 (AWS)
3. Hosted (RDS)
4. letsencrypt
Domain: central.yourdomain.com
```

**Auto-derived:**
```bash
DOMAIN=central.yourdomain.com
SSL_TYPE=letsencrypt
DB_HOST=my-db-rds.xxxxx.rds.amazonaws.com
DB_SSL=true              # Always true for managed services
S3_SERVER=https://my-bucket.s3.amazonaws.com
S3_BUCKET_NAME=my-bucket
S3_ACCESS_KEY=<aws-key>
S3_SECRET_KEY=<aws-secret>
# No EXTRA_SERVER_NAME needed (AWS S3 has its own cert)
```

**What starts:**
- All services except garage (no local S3 needed)
- postgres14 still runs (for backward compat, not used)

**Service connectivity:**
- Service connects to: RDS (external), AWS S3 (external), Enketo (local), pyxform (local)

---

## Storage Decisions and Implications

### Decision: S3 Storage

#### Option 1: None (PostgreSQL Blobs)

```
┌────────────┐
│  Service   │  Upload: INSERT blob INTO submission_attachments
│  Container │  Download: SELECT blob FROM submission_attachments
└────────────┘
       │
   ┌───▼────┐
   │   DB   │ ◄── Stores binary data directly
   └────────┘
```

**Pros:**
- Simplest setup, no extra container
- Works for small/medium deployments
- No credentials to manage

**Cons:**
- Database grows large
- Backups include binary data
- Not recommended for production

#### Option 2: Local Garage S3

```
┌────────────┐
│  Service   │  Uses: s3.putObject(), s3.presignedGetObject()
│  Container │
└────┬───────┘
     │ docker network (internal)
     │ S3_SERVER=https://odk-central.s3.domain
     │
  ┌──▼──────┐
  │ Garage   │ ◄── Virtual-hosted style: bucket.s3.domain/object
  │:3900    │
  └─────────┘
     │
  Docker volume: garage_data:/data
```

**Pros:**
- Local S3-compatible storage
- No external service needed
- Full control over storage
- Works behind corporate firewalls
- Single-server deployment friendly

**Cons:**
- Extra container to manage
- Storage on server disk
- Manual backups needed

#### Option 3: External S3 (AWS, MinIO)

```
┌────────────┐
│  Service   │  Uses: s3.putObject(), s3.presignedGetObject()
│  Container │
└────┬───────┘
     │ Internet
     │ S3_SERVER=https://bucket.s3.amazonaws.com
     │
  ┌──▼──────────────┐
  │ External S3     │ ◄── AWS S3, MinIO, etc.
  │ (AWS, etc.)     │
  └─────────────────┘
```

**Pros:**
- Managed service (AWS handles backups, scaling)
- Off-server storage
- Highly available
- Auto-scaling storage

**Cons:**
- External dependency
- Network cost
- Credentials to manage

---

## Secret Management

### 1. Enketo Secrets (Auto-generated, persisted)

```
┌──────────────┐
│ secrets      │ Generates on first run:
│ container    │ - enketo-secret (64 bytes)
└──────┬───────┘ - enketo-less-secret (32 bytes)
       │         - enketo-api-key (128 bytes)
       │
       ▼
┌────────────────────────┐
│ Docker volume: secrets │ (persists forever)
└────────────────────────┘
       ▲
       │ Mounted by:
   ┌───┴──────┬──────────┬───────┐
   │          │          │       │
secrets   service    enketo   (other services)
```

**Characteristics:**
- Generated once, never regenerated (unless volume deleted)
- Persists across container restarts
- Shared between services via Docker volume
- Not in .env (auto-generated)

### 2. Infrastructure Secrets (.env)

```
.env file (user-provided)
├─ DB_PASSWORD          ──→ docker-compose.yml ──→ service env var
├─ S3_ACCESS_KEY        ──→ docker-compose.yml ──→ service env var
├─ S3_SECRET_KEY        ──→ docker-compose.yml ──→ service env var
├─ EMAIL_PASSWORD       ──→ docker-compose.yml ──→ service env var
├─ OIDC_CLIENT_SECRET   ──→ docker-compose.yml ──→ service env var
└─ [others]

At container start:
env vars ──→ envsub.awk ──→ config.json (templated)
             (at runtime,  (in-memory,
              never baked   never on disk)
              in image)
```

**Key rule:** Change = restart container, NOT rebuild image

### 3. SSL Certificates

**selfsign:**
```
setup-odk.sh generates on first start
  ↓
/etc/selfsign/live/${DOMAIN}/privkey.pem
/etc/selfsign/live/${DOMAIN}/fullchain.pem
```

**letsencrypt:**
```
setup-odk.sh runs certbot
  ↓
Requests certificate via HTTP-01 challenge
  ↓
/etc/letsencrypt/live/${DOMAIN}/privkey.pem
/etc/letsencrypt/live/${DOMAIN}/fullchain.pem
```

**customssl:**
```
User places certificates in:
  files/local/customssl/live/local/privkey.pem
  files/local/customssl/live/local/fullchain.pem
```

**upstream:**
```
Upstream proxy (nginx on host) handles SSL
nginx container uses HTTP only (port 8080)
```

---

## Network Architecture

### Docker Networks

```
┌─────────────────────────────────────────┐
│ Network: central_default                │
│ (created by docker-compose)             │
├─────────────────────────────────────────┤
│ Services: service, nginx, enketo, etc.  │
│ DNS: service_name → container_ip        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Network: central_db_net (external)      │
│ (for local PostgreSQL on host)          │
├─────────────────────────────────────────┤
│ Services: postgres14, service           │
│ Usage: If DB_HOST=host.docker.internal  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Network: central_web (external)         │
│ (for frontend dev server)               │
├─────────────────────────────────────────┤
│ Services: nginx, client-dev (optional)  │
│ Usage: For dev Vite dev server          │
└─────────────────────────────────────────┘
```

### DNS Resolution

**Internal (container → container):**
```
Service container resolves "postgres14" via Docker DNS
↓
Docker DNS resolves postgres14 to container IP
↓
Connection to postgres14:5432 succeeds
```

**For S3 (Garage):**
```
Service needs to reach: odk-central.s3.central.local
↓
Docker DNS doesn't know about this domain (it's outside docker)
↓
Solution: Add extra_hosts in docker-compose.yml
service:
  extra_hosts:
    - "odk-central.s3.central.local:host-gateway"
↓
host-gateway (special DNS name) = host machine IP
```

**For external DB:**
```
Service needs to reach: my-db.xxxxx.rds.amazonaws.com
↓
Docker DNS forwards to host's DNS resolver
↓
Host DNS resolves to RDS endpoint IP
↓
Connection succeeds
```

---

## Health Checks and Startup

### startup-checks.sh Validates

1. ✅ .env exists
2. ✅ docker installed
3. ✅ docker-compose installed
4. ✅ External networks exist (create if needed)
5. ✅ PostgreSQL readiness (pg_isready)
6. ✅ Service startup (looks for "starting server" in logs)
7. ✅ nginx availability (nc -z localhost 80)

### Dependency Ordering

```
                                ┌─────────────┐
                                │   nginx     │
                                └──────┬──────┘
                                       │ depends_on
                      ┌────────────────┴────────────────┐
                      │                                 │
                    service                        (optionally enketo)
                    8383                           (but service
                      │ depends_on                  depends_on enketo)
         ┌────────────┼──────────┬──────────┬────────────┐
         │            │          │          │            │
       postgres14   secrets   enketo    pyxform       garage
       5432           │       8005       80            3900
         ▲            │                                  ▲
         │       ┌────┴──────┐                         │
         │       │            │                         │
     postgres   enketo_redis  │                    (optional,
     migration  (main, cache) │                     if S3 enabled)
                              │
                         ┌────┴────────┐
                         │             │
                      mail (25)   pyxform converter
```

---

## Rebuild vs Restart

### Build Time (Image Creation)

```
Dockerfile + context
    ↓
docker build
    ↓
Image (contains: code, templates, scripts, base OS)
    ↓
Registry (Docker Hub, etc.)
```

**What's baked in:**
- Application code
- Template files (*.template)
- Scripts (startup, SSL setup, migrations)
- Base OS and runtime

**What's NOT baked in:**
- .env values
- Secrets (Enketo or user)
- Generated config (config.json, client-config.json)
- Certificates

### Runtime (Container Start)

```
Image
    ↓
docker run + environment variables
    ↓
Container startup script runs
    ↓
Scripts read environment variables
    ↓
envsub.awk processes templates
    ↓
Generated config files (in-memory, ephemeral)
    ↓
Application starts with config
```

**Decision Matrix:**
| Change | Rebuild | Restart | Why |
|--------|---------|---------|-----|
| .env variable | ❌ No | ✅ Yes | Runtime templating |
| Application code | ✅ Yes | ✅ Yes | Baked in image |
| NGINX_BASE_IMAGE | ✅ Yes | ✅ Yes | Build-time ARG |
| Dockerfile | ✅ Yes | ✅ Yes | Image definition |
| SSL certificate | ❌ No | ✅ Yes | Generated at startup |
| Database password | ❌ No | ✅ Yes | Runtime templating |
| S3 credentials | ❌ No | ✅ Yes | Runtime templating |

---

## VG Fork Customizations

### What's Different from Upstream

1. **ModSecurity WAF**
   - Custom nginx base image: `drguptavivek/central-nginx-vg-base:6.0.1`
   - NGINX_BASE_IMAGE build-time ARG
   - CRS rules in ./crs/ directory

2. **Garage S3 Integration**
   - Garage container (dxflrs/garage:v2.1.0)
   - scripts/init-odk.sh (generates Garage config + overlay)
   - scripts/add-s3.sh (bootstraps layout/key/bucket)
   - S3 nginx routing configuration

3. **App User Authentication**
   - New endpoints: /login, /password/reset, /revoke
   - Session management: TTL + cap
   - VG-specific database tables: vg_settings, vg_field_key_auth, etc.

4. **Telemetry Features**
   - Data collection and export
   - Map visualization with OpenLayers

### Modularity for Rebasing

- VG customizations isolated in `vg-*` prefixed files
- Minimal core upstream edits (documented in docs/vg/)
- Easy to rebase onto upstream master

---

## Recommended Reading Order

1. **GETTING-STARTED.md** - For quick setup
2. **odk-routing-decision-points.md** - Understand the 4 decisions
3. **odk-routing-rules.md** - Understand routing constraints
4. **odk-secrets-env.md** - Understand secret management
5. **This file (ARCHITECTURE.md)** - Full system understanding

---

**Last Updated:** January 2025
