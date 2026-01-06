# ODK Central Routing Rules

**Based on upstream getodk/central master + VG Garage S3 integration**

---

## Default Service Ports (Upstream ODK Central)

| Service | Internal Port | Host Binding | Protocol | Purpose |
|---------|--------------|--------------|----------|---------|
| **nginx** | 80, 443 | `${HTTP_PORT}:80`, `${HTTPS_PORT}:443` | HTTP/HTTPS | Reverse proxy, SSL termination |
| **service** | 8383 | docker network only | HTTP | ODK backend API |
| **postgres14** | 5432 | docker network only | TCP | PostgreSQL database |
| **enketo** | 8005 | docker network only | HTTP | Form rendering engine |
| **enketo_redis_main** | 6379 | docker network only | TCP | Redis cache (main) |
| **enketo_redis_cache** | 6380 | docker network only | TCP | Redis cache (cache) |
| **pyxform** | 80 | docker network only | HTTP | XForm conversion |
| **mail** | 25 | docker network only | SMTP | Email delivery |

**VG Addition (Optional - only if using Garage for S3):**
| Service | Internal Port | Host Binding | Protocol | Purpose |
|---------|--------------|--------------|----------|---------|
| **garage** | 3900 | 127.0.0.1:3900 (optional) | HTTP | S3-compatible API |
| **garage** | 3903 | 127.0.0.1:3903 (optional) | HTTP | S3 Web UI |

---

## Routing Diagram

### Option A: With Garage S3 (VG Default)

```
┌──────────────────────────────────────────────────────────────────┐
│ EXTERNAL (Clients: ODK Collect, Web Browsers)                   │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                    HTTPS (443)
                         │
          ┌──────────────▼──────────────┐
          │  nginx (container)          │
          │  - SSL termination          │
          │  - Routes by Host header    │
          │  - Ports: 80,443 → host     │
          └──┬────────────┬─────────────┘
             │            │
        Host:│       Host:│
      ${DOMAIN}    bucket.s3.${DOMAIN}
             │            │
     ┌───────▼──────┐  ┌──▼─────────────┐
     │  service     │  │  garage        │
     │  Port: 8383  │  │  Ports: 3900   │
     │              │  │         3903   │
     └──┬───────────┘  └────────────────┘
        │
        ├─────────┬────────┬──────────┐
        │         │        │          │
   ┌────▼───┐ ┌──▼──┐ ┌───▼────┐ ┌───▼───┐
   │postgres│ │redis│ │enketo  │ │pyxform│
   └────────┘ └─────┘ └────────┘ └───────┘
```

### Option B: With External S3 (AWS S3, MinIO, etc.)

```
┌──────────────────────────────────────────────────────────────────┐
│ EXTERNAL (Clients: ODK Collect, Web Browsers)                   │
└────────┬──────────────────────────────┬────────────────────────┘
         │                              │
         │                         Direct to S3
    HTTPS (443)                         │
         │                              │
     ┌───▼─────────────┐       ┌────────▼────────────┐
     │  nginx          │       │  External S3        │
     │  (ODK only)     │       │  (AWS/MinIO/etc)    │
     └───┬─────────────┘       │  S3_SERVER          │
         │                     └─────────────────────┘
         │
     ┌───▼──────┐
     │  service │  ─────uploads───────┐
     │  8383    │                     │
     └──┬───────┘                     │
        │                             │
        ├─────────┬────────┬──────────┤
        │         │        │          │
   ┌────▼───┐ ┌──▼──┐ ┌───▼────┐ ┌───▼───┐
   │postgres│ │redis│ │enketo  │ │pyxform│
   └────────┘ └─────┘ └────────┘ └───────┘

No Garage container needed!
S3_SERVER = external URL (e.g., https://mybucket.s3.amazonaws.com)
```

---

## 10 Critical Routing Rules

### 1. S3 is Optional (Upstream Behavior)

```bash
# Upstream ODK Central .env.template:
# Optional: configure S3-compatible storage for binary files
# S3_SERVER=
# S3_ACCESS_KEY=
# S3_SECRET_KEY=
# S3_BUCKET_NAME=

# If S3_* vars are empty → blobs stored in PostgreSQL
# If S3_* vars are set → blobs stored in S3 (Garage or external)
```

**Rule:** S3 is optional; if not configured, ODK stores blobs in PostgreSQL (not recommended for production).

---

### 2. S3_SERVER Dual Purpose

ODK Service uses Minio client for **BOTH**:
- Uploading blobs: `putObject(bucket, object, stream)`
- Generating download URLs: `presignedGetObject(bucket, object, expiry)`

**Rule:** `S3_SERVER` must be accessible from Service container (uploads) AND from external clients (downloads).

---

### 3. Garage vs External S3

**Using Garage (VG default):**
```bash
S3_SERVER=https://odk-central.s3.${DOMAIN}
# Garage container required
# nginx must route S3 subdomain to garage:3900
# SSL cert must include S3 subdomain
```

**Using External S3 (AWS, MinIO, etc.):**
```bash
S3_SERVER=https://mybucket.s3.amazonaws.com
# OR
S3_SERVER=https://minio.mycompany.com/mybucket
# No Garage container needed
# No nginx S3 routing needed
# No S3 subdomain certificate needed (external S3 has its own)
```

**Rule:** Configuration depends on S3 provider (Garage local vs external service).

---

### 4. Garage Virtual-Hosted URL Format (Garage Only)

```toml
# garage/garage.toml (only if using Garage)
[s3_api]
root_domain = ".s3.${DOMAIN}"  # Note: leading dot
```

Garage expects bucket as subdomain:
```
✅ https://odk-central.s3.domain.com/blob-123  (virtual-hosted)
❌ https://s3.domain.com/odk-central/blob-123  (path-style, rejected)
```

**Rule (Garage only):** S3_SERVER must use format `https://${BUCKET}.s3.${DOMAIN}`.

---

### 5. Configuration Alignment (Garage Only)

```bash
# .env
S3_SERVER=https://odk-central.s3.central.yourdomain.com
S3_BUCKET_NAME=odk-central

# garage/garage.toml
[s3_api]
root_domain = ".s3.central.yourdomain.com"

# files/nginx/s3.conf
server_name odk-central.s3.central.yourdomain.com;
proxy_pass http://garage:3900;
```

**Rule (Garage only):** Bucket subdomain must be consistent across ODK, Garage, and nginx.

---

### 6. S3_SERVER Protocol

```bash
# Always HTTPS (even in development)
S3_SERVER=https://odk-central.s3.central.local  # Garage with self-signed
S3_SERVER=https://mybucket.s3.amazonaws.com     # External S3
S3_SERVER=https://odk-central.s3.yourdomain.com # Garage with Let's Encrypt

# Never HTTP
S3_SERVER=http://...  # ❌ Clients expect secure downloads
```

**Rule:** `S3_SERVER` must always use `https://` protocol (clients expect secure S3 downloads).

---

### 7. DNS Resolution (Internal & External)

**Service container needs to resolve S3_SERVER:**

For Garage:
```yaml
services:
  service:
    extra_hosts:
      - "odk-central.s3.central.local:host-gateway"
```

For External S3:
```
# No extra_hosts needed
# Service uses public DNS to reach external S3
```

**Clients need to resolve S3_SERVER:**
- Garage: DNS A records or `/etc/hosts` for S3 subdomain
- External S3: Public DNS (already configured by S3 provider)

**Rule:** For Garage, S3_SERVER domain must resolve both inside docker and from clients. For external S3, public DNS suffices.

---

### 8. Request Flow: Blob Upload vs Download

**Upload (Service → S3):**
```
Service container (Minio client)
  → S3_SERVER
  → [Garage: via nginx to garage:3900]
  → [External S3: direct via internet]
```

**Download (Client → S3):**
```
ODK Collect
  → Requests form from Service API
  → Service generates presigned URL using S3_SERVER
  → Returns 307 redirect to presigned URL
  → Client downloads directly from S3_SERVER
  → [Garage: via nginx to garage:3900]
  → [External S3: direct from S3 provider]
```

**Rule:** Downloads bypass Service (direct client → S3); upload routing depends on S3 provider.

---

### 9. Standard vs Upstream SSL Mode

**Standard (selfsign/letsencrypt/customssl):**
```bash
HTTP_PORT=80
HTTPS_PORT=443
# nginx container binds to host ports 80 and 443
```

**Upstream (behind reverse proxy):**
```bash
HTTP_PORT=8080  # Different! Avoids conflict with upstream proxy
HTTPS_PORT=8443 # Not used
S3_SERVER=https://odk-central.s3.domain.com  # Still public HTTPS URL

# Upstream proxy (on host) uses 80/443, forwards to localhost:8080
```

**Rule:** Upstream mode must use non-standard HTTP_PORT; S3_SERVER remains public HTTPS URL.

---

### 10. Upstream Proxy Headers (All Domains)

```nginx
# Upstream nginx/proxy MUST set for ALL domains (ODK + S3)

# Main ODK Central domain
server {
  listen 443 ssl;
  server_name central.yourdomain.com;

  location / {
    proxy_pass http://localhost:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}

# S3 subdomain (if using Garage)
server {
  listen 443 ssl;
  server_name odk-central.s3.yourdomain.com;

  location / {
    proxy_pass http://localhost:8080;
    proxy_set_header Host $host;  # CRITICAL: Garage routing depends on this
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

**Rule:** Upstream proxy must preserve `Host` header and set `X-Forwarded-Proto: https` for **all** proxied domains (both ODK and S3).

---

## Quick Validation Checklist

```bash
# 1. Check if S3 is configured
grep -q "^S3_SERVER=" .env && echo "S3 enabled" || echo "S3 disabled (PostgreSQL blobs)"

# 2. If S3 enabled, check format
[ -n "$S3_SERVER" ] && echo $S3_SERVER | grep -E "^https://"
# Should match: https://...

# 3. If using Garage, check virtual-hosted format
[ -f garage/garage.toml ] && echo $S3_SERVER | grep -E "^https://.*\.s3\."
# Should match: https://bucket.s3.domain

# 4. If using Garage, check root_domain matches
[ -f garage/garage.toml ] && grep "root_domain" garage/garage.toml
# Should be: ".s3.${DOMAIN}"

# 5. If using Garage, check S3 domain resolves from Service
[ -f garage/garage.toml ] && docker compose exec service getent hosts $(echo $S3_SERVER | sed 's|https://||' | cut -d'/' -f1)
# Should return IP

# 6. For upstream mode: HTTP_PORT != 80
[ "$SSL_TYPE" = "upstream" ] && grep HTTP_PORT .env
# Should be 8080 if SSL_TYPE=upstream

# 7. For letsencrypt + Garage: S3 domains in EXTRA_SERVER_NAME
[ "$SSL_TYPE" = "letsencrypt" ] && [ -f garage/garage.toml ] && grep EXTRA_SERVER_NAME .env
# Should include S3 subdomains
```

---

## Common Issues

| Problem | Symptom | Cause | Solution |
|---------|---------|-------|----------|
| Clients can't download (Garage) | 404/timeout | Wrong S3_SERVER format | Use `https://bucket.s3.domain` |
| Service can't upload (Garage) | Connection refused | S3_SERVER not resolvable | Add to extra_hosts |
| Garage returns 403 | Signature invalid | Wrong S3_SECRET_KEY | Regenerate credentials |
| nginx port conflict | Failed to start | Port 80/443 in use | Use upstream mode (HTTP_PORT=8080) |
| Missing S3 cert (Garage) | SSL error | Not in EXTRA_SERVER_NAME | Add S3 domains to EXTRA_SERVER_NAME |
| External S3 upload fails | Access denied | Wrong credentials | Check S3_ACCESS_KEY/SECRET_KEY |

---

**End of Document**
