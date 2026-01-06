# ODK Central Routing Decision Points

**Simple decision matrix - answer 4 questions + domain, configuration flows automatically**

---

## The 4 Key Decisions

```
1. Environment Type:     Dev | Prod
2. S3 Storage:          None (PostgreSQL) | Local (Garage) | External Provider
3. PostgreSQL Instance:  Container | Local PostgreSQL | Hosted Service
4. SSL Termination:      selfsign | letsencrypt | customssl | upstream
```

**Plus:** `DOMAIN` (e.g., `central.local` or `central.yourdomain.com`)

**Result:** All other configuration derives from these choices.

---

## Decision Matrix → Auto Configuration

| # | Environment | S3 | Database | SSL | Domain | → Auto-Derived Config |
|---|-------------|----|-----------|----|---------|----------------------|
| **1** | Dev | None | Local | selfsign | `central.local` | `HTTP_PORT=80`, `HTTPS_PORT=443`, No S3 vars, DB defaults, `/etc/hosts` |
| **2** | Dev | Garage | Local | selfsign | `central.local` | `HTTP_PORT=80`, `HTTPS_PORT=443`, `S3_SERVER=https://odk-central.s3.central.local`, DB defaults, Garage container, `/etc/hosts` |
| **3** | Prod | Garage | Local | letsencrypt | `central.yourdomain.com` | `HTTP_PORT=80`, `HTTPS_PORT=443`, `S3_SERVER=https://odk-central.s3.central.yourdomain.com`, `EXTRA_SERVER_NAME=odk-central.s3...`, DB defaults, Garage container, Public DNS A records |
| **4** | Prod | External S3 | Local | letsencrypt | `central.yourdomain.com` | `HTTP_PORT=80`, `HTTPS_PORT=443`, `S3_SERVER=https://mybucket.s3.amazonaws.com`, DB defaults, No Garage, Public DNS |
| **5** | Prod | External S3 | External | letsencrypt | `central.yourdomain.com` | `HTTP_PORT=80`, `HTTPS_PORT=443`, `S3_SERVER=https://mybucket.s3.amazonaws.com`, `DB_HOST=rds.endpoint`, No Garage, Public DNS |
| **6** | Prod | Garage | Local | customssl | `central.corp.internal` | `HTTP_PORT=80`, `HTTPS_PORT=443`, `S3_SERVER=https://odk-central.s3.central.corp.internal`, Certs in `files/local/customssl/`, Garage container, Internal DNS |
| **7** | Prod | External S3 | External | upstream | `central.yourdomain.com` | `HTTP_PORT=8080`, `HTTPS_PORT=8443`, `S3_SERVER=https://mybucket.s3.amazonaws.com`, `DB_HOST=rds.endpoint`, No Garage, Upstream proxy config |
| **8** | Prod | Garage | Local | upstream | `central.yourdomain.com` | `HTTP_PORT=8080`, `HTTPS_PORT=8443`, `S3_SERVER=https://odk-central.s3.yourdomain.com`, DB defaults, Garage container, Upstream proxy handles SSL for all domains |

---

## Auto-Derived Configuration Rules

### From Environment Type

| Environment | Implies |
|-------------|---------|
| **Dev** | `DOMAIN=*.local`, Self-signed certs OK, `/etc/hosts` for DNS, Can use PostgreSQL blobs |
| **Prod** | Real domain, Valid SSL required, Public/Internal DNS, **S3 recommended** (PostgreSQL blobs acceptable for small scale) |

---

### From S3 Storage Choice

| S3 Choice | Auto-Derived |
|-----------|--------------|
| **None** | No S3 vars in .env, Blobs in PostgreSQL, No Garage container, No S3 subdomain cert |
| **Garage** | `S3_SERVER=https://${S3_BUCKET_NAME}.s3.${DOMAIN}`, Garage container, S3 subdomain cert needed, nginx s3.conf, `S3_ACCESS_KEY` & `S3_SECRET_KEY` generated |
| **External** | `S3_SERVER=https://external-s3-url`, No Garage container, No S3 subdomain cert, External credentials |

---

### From PostgreSQL Instance

| DB Choice | Auto-Derived |
|-----------|--------------|
| **Container** | postgres14 container in docker-compose, `DB_HOST=postgres14`, `DB_USER=odk`, `DB_PASSWORD=odk`, `DB_NAME=odk`, `DB_SSL=null` |
| **Local PostgreSQL** | No container, `DB_HOST=localhost` or `host.docker.internal`, Custom credentials, `DB_SSL=null` or `true` (depends on pg_hba.conf) |
| **Hosted Service** | No container, `DB_HOST=external.endpoint` (RDS/CloudSQL/Azure), Custom credentials, `DB_SSL=true` (required by providers) |

---

### From SSL Termination

| SSL Type | Auto-Derived |
|----------|--------------|
| **selfsign** | `HTTP_PORT=80`, `HTTPS_PORT=443`, Auto-generated certs, nginx handles SSL, Browser warnings expected |
| **letsencrypt** | `HTTP_PORT=80`, `HTTPS_PORT=443`, `EXTRA_SERVER_NAME` for S3 subdomains (if Garage), Public DNS required, Ports 80/443 open |
| **customssl** | `HTTP_PORT=80`, `HTTPS_PORT=443`, Certs at `files/local/customssl/live/local/`, nginx handles SSL, Manual renewal |
| **upstream** | `HTTP_PORT=8080`, `HTTPS_PORT=8443`, Upstream proxy handles SSL, nginx uses HTTP only, Upstream sets headers |

---

### From Domain

| Domain Type | Implies |
|-------------|---------|
| `*.local` | `/etc/hosts` entries, Self-signed SSL, Development only |
| Real domain | DNS A records (public or internal), Valid SSL, Production ready |

---

## Configuration Generation Template

```bash
# Based on decisions, auto-fill .env:

# Decision 1: Environment
# (No direct .env var, informs other choices)

# Decision 2 + 5: S3 + Domain
if [ S3_CHOICE = "None" ]; then
  # No S3 vars
  :
elif [ S3_CHOICE = "Garage" ]; then
  S3_SERVER=https://${S3_BUCKET_NAME}.s3.${DOMAIN}
  S3_BUCKET_NAME=odk-central
  S3_ACCESS_KEY=<generated>
  S3_SECRET_KEY=<generated>
elif [ S3_CHOICE = "External" ]; then
  S3_SERVER=https://external-s3-url
  S3_BUCKET_NAME=<external-bucket>
  S3_ACCESS_KEY=<external-key>
  S3_SECRET_KEY=<external-secret>
fi

# Decision 3: Database
if [ DB_CHOICE = "Local" ]; then
  # Use defaults (commented in .env)
  :
elif [ DB_CHOICE = "External" ]; then
  DB_HOST=<external-endpoint>
  DB_USER=<external-user>
  DB_PASSWORD=<external-password>
  DB_NAME=<external-dbname>
  DB_SSL=true
fi

# Decision 4: SSL
SSL_TYPE=<selfsign|letsencrypt|customssl|upstream>
if [ SSL_TYPE = "upstream" ]; then
  HTTP_PORT=8080
  HTTPS_PORT=8443
else
  HTTP_PORT=80
  HTTPS_PORT=443
fi

if [ SSL_TYPE = "letsencrypt" ] && [ S3_CHOICE = "Garage" ]; then
  EXTRA_SERVER_NAME=${S3_BUCKET_NAME}.s3.${DOMAIN} web.${DOMAIN}
fi

# Decision 5: Domain
DOMAIN=<user-provided>
SYSADMIN_EMAIL=<user-provided>
```

---

## Quick Reference: Common Combinations

### Dev: Minimal
```
Environment: Dev
S3: None
Database: Local
SSL: selfsign
Domain: central.local
```
**Result:** Simplest possible setup, PostgreSQL blobs, self-signed cert.

---

### Dev: Garage S3
```
Environment: Dev
S3: Garage
Database: Local
SSL: selfsign
Domain: central.local
```
**Result:** Test S3 integration locally, self-signed cert.

---

### Prod: VM/VPS
```
Environment: Prod
S3: Garage
Database: Local
SSL: letsencrypt
Domain: central.yourdomain.com
```
**Result:** Production-ready single server, free SSL, local S3.

---

### Prod: Cloud Native
```
Environment: Prod
S3: External (AWS S3)
Database: External (AWS RDS)
SSL: letsencrypt or upstream
Domain: central.yourdomain.com
```
**Result:** Fully managed infrastructure, scalable.

---

### Prod: Corporate/Private Infra/DC
```
Environment: Prod
S3: Garage
Database: Local
SSL: customssl or upstream
Domain: central.corp.internal
```
**Result:** Private network, corporate certificates, on-premises.

---

## DNS Configuration (Auto-Derived from Choices)

### If S3 = None or External
```
# Only main domain needed
central.yourdomain.com → server-ip
```

### If S3 = Garage
```
# Main domain + S3 subdomains
central.yourdomain.com                    → server-ip
odk-central.s3.central.yourdomain.com     → server-ip
web.central.yourdomain.com                → server-ip
```

### If Domain = *.local
```
# /etc/hosts instead of DNS
127.0.0.1  central.local odk-central.s3.central.local web.central.local
```

---

## Services Started (Auto-Derived from Choices)

```
Base services (always):
- nginx
- service
- enketo
- enketo_redis_main
- enketo_redis_cache
- pyxform
- mail
- secrets

+ If Database=Local:
  - postgres14

+ If S3=Garage:
  - garage

+ If Environment=Dev and client/ exists:
  - client-dev
```

---

## Init Script Selection (Auto-Derived)

```
if [ Environment = "Dev" ]; then
  bash scripts/init-dev.sh
elif [ Environment = "Prod" ]; then
  bash scripts/init-prod.sh
fi

# Script auto-detects from .env:
# - SSL_TYPE → SSL setup
# - S3_* vars → Garage setup or skip
# - DB_HOST → External DB or local postgres14
# - HTTP_PORT → Standard or upstream mode
```

---

**End of Document**

The key insight: **Answer 4 questions + provide domain → everything else is deterministic.**
