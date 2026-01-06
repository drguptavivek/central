# ODK Central VG Fork - Getting Started

## Quick Start (3 Steps)

### 1. Initialize Configuration

```bash
./scripts/init-odk.sh
```

This interactive script guides you through 4 key decisions:

1. **Environment Type**: Dev or Prod
2. **S3 Storage**: None (PostgreSQL) | Local Garage | External S3
3. **PostgreSQL**: Container | Local | Hosted Service
4. **SSL**: selfsign | letsencrypt | customssl | upstream

The script auto-generates `.env` with complete configuration.

### 2. Start the Stack

```bash
./scripts/start-stack.sh
```

This script:
- Validates your configuration
- Creates Docker networks
- Starts services in dependency order
- Waits for health checks
- Provides access information

### 3. Access ODK Central

```
Web UI:  https://central.local  (or your configured DOMAIN)
API:     https://central.local/v1
```

---

## What Each Script Does

### `scripts/init-odk.sh` - Interactive Setup

**Purpose:** Configure ODK Central for your environment

**Interactive Prompts:**
1. Environment Type (Dev/Prod)
2. S3 Storage option (None/Garage/External)
3. Database option (Container/Local/Hosted)
4. SSL termination (selfsign/letsencrypt/customssl/upstream)
5. Domain name (e.g., central.local, central.yourdomain.com)
6. Sysadmin email (for Let's Encrypt notifications)

**Outputs:**
- `.env` - Complete configuration file
- `.env.backup` - Previous .env (if exists)
- `garage/garage.toml` - Garage S3 config (if S3=Garage)

**Run:**
```bash
./scripts/init-odk.sh
```

**Flow Diagram:**
```
init-odk.sh
├─ Ask 4 decisions
├─ Ask Domain + Email
├─ Auto-derive configuration
│  ├─ Ports (80/443 or 8080/8443)
│  ├─ S3_SERVER URL
│  ├─ SSL type + certs path
│  └─ DB connection string
├─ Generate .env
└─ Setup Garage (if selected)
```

### `scripts/start-stack.sh` - Start Services

**Purpose:** Start ODK Central with validation and health checks

**Pre-checks:**
- `.env` file exists
- Docker installed
- Docker Compose installed

**Actions:**
1. Create external Docker networks (`central_db_net`, `central_web`)
2. Start all services with `docker-compose up -d`
3. Wait for PostgreSQL readiness
4. Wait for ODK Service startup
5. Wait for nginx availability
6. Display access information and next steps

**Run:**
```bash
./scripts/start-stack.sh
```

**Output:**
```
✓ ODK Central stack is running!

Access Points:
  Web UI:    https://central.local:443
  API:       https://central.local:443/v1
  S3 API:    https://odk-central.s3.central.local

Useful Commands:
  View logs:        docker compose logs -f service
  Check status:     docker compose ps
  ...
```

---

## Configuration Decision Matrix

Based on your answers to the 4 questions, everything else is auto-configured:

| # | Environment | S3 | Database | SSL | Auto-Derived Config |
|---|-------------|----|-----------|----|-----|
| 1 | Dev | None | Container | selfsign | HTTP_PORT=80, HTTPS_PORT=443, blobs in PostgreSQL, /etc/hosts |
| 2 | Dev | Garage | Container | selfsign | + S3_SERVER, Garage container, S3 cert |
| 3 | Prod | Garage | Container | letsencrypt | + Let's Encrypt multi-domain cert, public DNS |
| 4 | Prod | External | Container | letsencrypt | + S3_SERVER to external provider, simple cert |
| 5 | Prod | External | Hosted | letsencrypt | + DB_HOST external, DB_SSL=true |
| 6 | Prod | Garage | Local | customssl | + Custom certs from files/local/customssl/ |
| 7 | Prod | External | Hosted | upstream | HTTP_PORT=8080, HTTPS_PORT=8443, upstream proxy handles SSL |

See `docs/vg/odk-routing-decision-points.md` for detailed auto-derivation rules.

---

## Common Scenarios

### Scenario 1: Local Development (Minimal)

```bash
./scripts/init-odk.sh
# Answers:
# 1. Dev
# 2. None (blobs in PostgreSQL)
# 3. Container (postgres14)
# 4. selfsign (dev certs)
# Domain: central.local

./scripts/start-stack.sh
# Add to /etc/hosts: 127.0.0.1 central.local
# Access: https://central.local
```

### Scenario 2: Development with S3 (Testing uploads)

```bash
./scripts/init-odk.sh
# Answers:
# 1. Dev
# 2. Local Garage (test S3 integration)
# 3. Container
# 4. selfsign
# Domain: central.local

./scripts/start-stack.sh
# Add to /etc/hosts:
#   127.0.0.1 central.local
#   127.0.0.1 odk-central.s3.central.local
#   127.0.0.1 web.central.local
```

### Scenario 3: Production (Single Server, Let's Encrypt)

```bash
./scripts/init-odk.sh
# Answers:
# 1. Prod
# 2. Local Garage (recommended for single-server)
# 3. Container (local PostgreSQL is fine for single-server)
# 4. letsencrypt (free automated SSL)
# Domain: central.yourdomain.com
# Email: admin@yourdomain.com

# Setup DNS A records:
# central.yourdomain.com → your-server-ip
# odk-central.s3.central.yourdomain.com → your-server-ip
# web.central.yourdomain.com → your-server-ip

./scripts/start-stack.sh
# Let's Encrypt will issue certificate automatically
```

### Scenario 4: Production (Cloud Native, AWS)

```bash
./scripts/init-odk.sh
# Answers:
# 1. Prod
# 2. External S3 (AWS S3)
# 3. Hosted (AWS RDS)
# 4. letsencrypt
# Domain: central.yourdomain.com
# S3_SERVER: https://my-bucket.s3.amazonaws.com
# DB_HOST: my-db.xxxxx.rds.amazonaws.com

./scripts/start-stack.sh
```

### Scenario 5: Behind Corporate Proxy

```bash
./scripts/init-odk.sh
# Answers:
# 1. Prod
# 2. Local Garage (internal network)
# 3. Container (or Hosted)
# 4. upstream (let corporate proxy handle SSL)
# Domain: central.corp.internal
# Sysadmin Email: admin@corp.internal

# Setup upstream nginx on proxy server with:
#   - listen 443 ssl (corporate certificates)
#   - proxy_pass http://odk-server:8080
#   - proxy_set_header X-Forwarded-Proto https

./scripts/start-stack.sh
```

---

## Changing Configuration Later

If you need to change configuration after initial setup:

### Change S3 Credentials
```bash
vim .env          # Update S3_ACCESS_KEY, S3_SECRET_KEY
docker compose restart service
```

### Change Domain
```bash
vim .env          # Update DOMAIN
docker compose restart service nginx enketo
```

### Change Database
```bash
vim .env          # Update DB_HOST, DB_PASSWORD, etc.
docker compose restart service
```

### Change SSL Type
```bash
vim .env          # Update SSL_TYPE, HTTP_PORT, HTTPS_PORT
docker compose restart nginx
# May need to regenerate certificates
```

See `docs/vg/odk-secrets-env.md` for details on what requires rebuilds vs restarts.

---

## Troubleshooting

### Service won't start
```bash
# Check logs
docker compose logs service | tail -50

# Common issues:
# - Database connection failed: Check DB_HOST, DB_PASSWORD
# - Port already in use: Change HTTP_PORT/HTTPS_PORT or stop other services
# - Certificate error: Check SSL_TYPE and certificate files
```

### Garage not accessible
```bash
# Check Garage is running
docker compose ps garage

# Check Garage logs
docker compose logs garage

# Verify S3 config
cat garage/garage.toml
docker compose exec service env | grep S3_

# Test connectivity
docker compose exec service nc -zv garage 3900
```

### Certificate issues (Let's Encrypt)
```bash
# Check nginx logs
docker compose logs nginx | grep -i cert

# Verify domain resolves
nslookup central.yourdomain.com

# Check Let's Encrypt logs
docker compose logs nginx | grep -i certbot
```

### Database migration issues
```bash
# Check migration logs
docker compose logs service | grep -i migration

# Manually run migrations
docker compose exec service node ./lib/bin/run-migrations
```

---

## Full Workflow

```bash
# 1. Clone the repo
git clone https://github.com/drguptavivek/central.git
cd central

# 2. Initialize configuration
./scripts/init-odk.sh

# 3. Review generated config
cat .env

# 4. Start the stack
./scripts/start-stack.sh

# 5. Access ODK Central
# Open: https://central.local (or your configured domain)

# 6. Create default user
# Web UI will prompt for first user account

# 7. Start collecting data!
```

---

## Understanding Your Configuration

After running `init-odk.sh`, your `.env` contains the complete configuration:

```bash
# These 4 lines document your decisions
DOMAIN=central.local
SSL_TYPE=selfsign
DB_HOST=postgres14
S3_SERVER=https://odk-central.s3.central.local

# Everything else is auto-derived from these decisions
HTTP_PORT=80
HTTPS_PORT=443
DB_USER=odk
DB_PASSWORD=odk
S3_BUCKET_NAME=odk-central
# etc.
```

To understand how a setting is derived, see:
- `docs/vg/odk-routing-decision-points.md` - Auto-derivation rules
- `docs/vg/odk-routing-rules.md` - Routing and configuration constraints
- `docs/vg/odk-secrets-env.md` - How secrets are managed

---

## Documentation

- **Quick Reference**: This file (GETTING-STARTED.md)
- **Routing Decisions**: `docs/vg/odk-routing-decision-points.md`
- **Routing Rules**: `docs/vg/odk-routing-rules.md`
- **Secrets Management**: `docs/vg/odk-secrets-env.md`
- **VG Client Changes**: `docs/vg/vg-client/vg_client_changes.md`
- **VG Server Changes**: `docs/vg/vg-server/vg_api.md`

---

## Need Help?

- Check logs: `docker compose logs -f <service-name>`
- Review configuration: `cat .env`
- Re-run setup: `./scripts/init-odk.sh` (it will back up your current .env)
- Read the routing documentation: `docs/vg/odk-routing-*.md`

---

**Happy deploying!** 🚀
