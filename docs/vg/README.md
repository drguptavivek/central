# ODK Central VG Fork Documentation

Complete documentation for the VG (Vivek Gupta) fork of ODK Central with integrated Garage S3 storage, ModSecurity WAF, and enhanced app user authentication.

---

## 📚 Quick Navigation

### For First-Time Users

1. **[GETTING-STARTED.md](GETTING-STARTED.md)** ← **START HERE**
   - 3-step quick start guide
   - Interactive setup scripts
   - Common scenarios with examples

### For Understanding Configuration

2. **[odk-routing-decision-points.md](odk-routing-decision-points.md)**
   - The 4 key decisions explained
   - How configuration auto-derives
   - Decision matrix with all combinations

3. **[odk-routing-rules.md](odk-routing-rules.md)**
   - 10 critical routing rules
   - Upstream proxy configuration
   - S3 (Garage vs External) constraints
   - Troubleshooting checklist

### For Understanding Secrets & Environment

4. **[odk-secrets-env.md](odk-secrets-env.md)**
   - How .env maps to containers
   - Build time vs runtime configuration
   - Secret lifecycle and rotation
   - Impact of changing .env (rebuild vs restart)

### For Deep Understanding

5. **[ARCHITECTURE.md](ARCHITECTURE.md)**
   - Complete system architecture
   - Service dependencies and startup order
   - Network topology
   - Storage options in detail
   - Configuration flow diagrams

---

## 📋 Document Index

| Document | Purpose | For Whom |
|----------|---------|----------|
| **GETTING-STARTED.md** | Quick start, examples, troubleshooting | Everyone |
| **odk-routing-decision-points.md** | Configuration decision matrix | Operators, Architects |
| **odk-routing-rules.md** | Routing constraints, SSL, S3 | DevOps, Network Engineers |
| **odk-secrets-env.md** | Secret management, env vars | Operators, Security |
| **ARCHITECTURE.md** | System design, service interaction | Architects, Developers |

---

## 🚀 Quick Start

### Option A: Interactive Setup (Recommended)

```bash
# 1. Run interactive setup wizard
./scripts/init-odk.sh

# 2. Review generated configuration
cat .env

# 3. Build + start
docker compose build
docker compose up -d

# 4. Access at https://central.local (or your domain)
```

### Option B: Manual Setup

```bash
# 1. Copy and edit template
cp .env.template .env
vim .env

# 2. Create networks
docker network create central_db_net central_web

# 3. Start services
docker compose up -d

# 4. Monitor startup
docker compose logs -f service
```

---

## 🎯 Common Tasks

### I want to...

**Set up ODK Central for the first time**
→ Read: [GETTING-STARTED.md](GETTING-STARTED.md)

**Choose between PostgreSQL vs Hosted Database**
→ Read: [odk-routing-decision-points.md](odk-routing-decision-points.md#from-postgresql-instance)

**Set up S3 storage (Garage vs AWS vs MinIO)**
→ Read: [odk-routing-rules.md](odk-routing-rules.md#3-garage-vs-external-s3)

**Change S3 credentials without rebuilding**
→ Read: [odk-secrets-env.md](odk-secrets-env.md#4-impact-of-changing-env)

**Understand the complete system**
→ Read: [ARCHITECTURE.md](ARCHITECTURE.md)

**Configure Let's Encrypt for production**
→ Read: [odk-routing-decision-points.md](odk-routing-decision-points.md#from-ssl-termination)

**Set up behind a corporate proxy**
→ Read: [odk-routing-rules.md](odk-routing-rules.md#9-standard-vs-upstream-ssl-mode)

**Rotate database passwords**
→ Read: [odk-secrets-env.md](odk-secrets-env.md#scenario-2-change-database-password)

**Troubleshoot S3 connectivity**
→ Read: [odk-routing-rules.md](odk-routing-rules.md#common-issues)

---

## 🔧 Configuration at a Glance

### The 4 Key Decisions

```
1. Environment Type
   Dev ........................ Development/localhost
   Prod ....................... Production/public domain

2. S3 Storage
   None ....................... Blobs in PostgreSQL (simple)
   Local Garage ............... S3-compatible container (recommended)
   External S3 ................ AWS, MinIO, etc. (cloud-native)

3. Database
   Container .................. postgres14 in docker-compose
   Local PostgreSQL ........... PostgreSQL on host machine
   Hosted Service ............. AWS RDS, Google Cloud SQL, etc.

4. SSL Termination
   selfsign ................... Self-signed (dev only)
   letsencrypt ................ Automated HTTPS (free)
   customssl .................. Your own certificates
   upstream ................... Behind reverse proxy
```

**Answer these 4 questions + provide domain → complete auto-configuration** ✓

---

## 📦 What's Included

### Container Images
- **nginx** (ModSecurity WAF, custom base image)
- **service** (ODK Central API)
- **postgres14** (Database)
- **enketo** (Form rendering)
- **garage** (S3-compatible storage)
- **pyxform** (XForm compiler)
- **mail** (Email delivery)
- **secrets** (Enketo key generation)
- **enketo_redis_main/cache** (Redis caches)

### Scripts
- **scripts/init-odk.sh** - Interactive configuration wizard
- **scripts/add-s3.sh** - Bootstrap Garage (optional, S3=Garage only)

### VG Customizations
- App User authentication (username/password, sessions, 2FA-ready)
- Telemetry collection and visualization
- ModSecurity WAF integration
- Garage S3 integration
- Enhanced status endpoints

---

## 🔐 Key Features

### Security
- ModSecurity WAF via custom nginx image
- Support for Let's Encrypt SSL (free, automated)
- Custom SSL certificate support
- Upstream proxy support for corporate environments
- Session management with TTL and cap

### Flexibility
- Choose PostgreSQL container, local, or hosted (RDS, CloudSQL)
- Choose S3 storage: None, local Garage, or external (AWS, MinIO)
- Choose SSL: self-signed, Let's Encrypt, custom, or upstream
- Choose environment: development or production

### Simplicity
- 4 key decisions → auto-configured everything
- Interactive setup script (scripts/init-odk.sh)
- Optional Garage bootstrap script (scripts/add-s3.sh)
- Clear documentation for each decision

### Observability
- Telemetry collection
- Map visualization
- Enhanced logging
- Status endpoints

---

## 📖 Document Descriptions

### GETTING-STARTED.md
Entry point for all users. Covers:
- 3-step quick start
- What each script does
- Common scenarios (dev, prod, cloud, corporate)
- Troubleshooting guide
- Full workflow walkthrough

### odk-routing-decision-points.md
Decision matrix and auto-derivation rules. Explains:
- 4 key decisions in detail
- What configuration auto-derives from each decision
- 8 real-world combinations and what they produce
- Auto-derivation template (pseudo-code)
- Quick reference for common combinations

### odk-routing-rules.md
10 critical constraints that any configuration must follow. Explains:
- S3 is optional (upstream default behavior)
- S3_SERVER dual purpose (uploads + presigned URLs)
- Garage vs External S3 architecture
- Virtual-hosted URL format (required for Garage)
- DNS resolution (internal vs external)
- Upload vs Download request flows
- SSL mode (standard vs upstream)
- Upstream proxy headers
- Validation checklist
- Troubleshooting matrix

### odk-secrets-env.md
How secrets are managed and how .env maps to containers. Explains:
- Secret types (Enketo auto-generated vs infrastructure)
- Runtime configuration templating
- Environment variable passing
- Impact of changing .env (rebuild vs restart)
- Secrets lifecycle examples
- Security best practices
- Troubleshooting guide
- Build time vs runtime distinction

### ARCHITECTURE.md
Complete system design and understanding. Explains:
- Decision → config → services flow
- Service architecture (12 containers, ports, networking)
- Configuration templating process
- Storage architecture for each option
- Secret management in detail
- Network topology (Docker networks, DNS, external DB)
- Health checks and startup ordering
- Build time vs runtime (with decision matrix)
- Diagrams for visual understanding

---

## ❓ FAQ

**Q: Do I need to edit YAML files?**
A: No! Use `scripts/init-odk.sh` to generate everything automatically.

**Q: What if I need to change configuration later?**
A: Edit `.env` and restart relevant containers. See [odk-secrets-env.md](odk-secrets-env.md#4-impact-of-changing-env).

**Q: Do I need to rebuild the image to change S3 credentials?**
A: No! Change `.env` and restart the service container. See [odk-secrets-env.md](odk-secrets-env.md#build-time-vs-runtime).

**Q: What's the difference between Garage and external S3?**
A: Garage is a local container, external S3 is AWS/MinIO. See [odk-routing-rules.md](odk-routing-rules.md#3-garage-vs-external-s3).

**Q: Can I use this in production?**
A: Yes! See [GETTING-STARTED.md](GETTING-STARTED.md#scenario-3-production-single-server-lets-encrypt) for production setup.

**Q: Can I put this behind a corporate proxy?**
A: Yes! Choose `SSL_TYPE=upstream`. See [odk-routing-rules.md](odk-routing-rules.md#9-standard-vs-upstream-ssl-mode).

**Q: How do I troubleshoot S3 connectivity?**
A: See [odk-routing-rules.md](odk-routing-rules.md#quick-validation-checklist) for validation and [odk-routing-rules.md](odk-routing-rules.md#common-issues) for common issues.

---

## 📞 Getting Help

1. **For setup issues**: Read [GETTING-STARTED.md](GETTING-STARTED.md#troubleshooting)
2. **For configuration questions**: Read [odk-routing-decision-points.md](odk-routing-decision-points.md)
3. **For routing/networking issues**: Read [odk-routing-rules.md](odk-routing-rules.md)
4. **For secret/environment issues**: Read [odk-secrets-env.md](odk-secrets-env.md)
5. **For deep understanding**: Read [ARCHITECTURE.md](ARCHITECTURE.md)
6. **For everything else**: Check logs with `docker compose logs -f <service>`

---

## 📝 Version Information

- **Based on**: getodk/central master branch
- **VG Customizations**: App user auth, telemetry, ModSecurity, Garage S3
- **Last Updated**: January 2025
- **Garage Version**: v2.1.0
- **Nginx Base**: Custom VG image with ModSecurity

---

## 🗺️ Related Directories

```
.
├── scripts/                   # Initialization and utility scripts
│   ├── init-odk.sh           # Main setup wizard
│   └── add-s3.sh             # Bootstrap Garage (optional)
│
├── docs/vg/                   # VG customization documentation
│   ├── README.md             # This file (navigation hub)
│   ├── GETTING-STARTED.md    # Quick start guide
│   ├── ARCHITECTURE.md       # System architecture
│   ├── odk-routing-decision-points.md
│   ├── odk-routing-rules.md
│   ├── odk-secrets-env.md
│   ├── vg-client/            # Client-specific docs
│   └── vg-server/            # Server-specific docs
│
├── docker-compose.yml         # Main service definitions
├── docker-compose-garage.yml  # Optional Garage overlay (generated)
├── .env.template             # Environment variable template
└── garage/                     # Garage S3 configuration
    ├── garage.toml.example   # Example template (no secrets)
    ├── garage.toml           # Generated by init script (gitignored)
    └── storage.conf          # Garage capacity (gitignored)
```

---

**Ready to get started? → [GETTING-STARTED.md](GETTING-STARTED.md)** 🚀
