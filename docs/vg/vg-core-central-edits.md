# VG Core Central Meta-Repo Edits

**Updated:** 2026-01-14
**Repository:** `drguptavivek/central` (meta-repo)
**Upstream:** `getodk/central`
**Base Version:** v2025.4.1

---

## Overview

This document tracks all modifications made to the ODK Central meta-repo that deviate from upstream. Following the **minimal fork philosophy**, we keep changes to a minimum and document all deviations for easy rebasing and maintenance.

### Philosophy

1. **Keep docker-compose.yml pure upstream** - Makes future updates trivial
2. **Isolate security configs** - Put all modsecurity/CRS in override files
3. **Document all changes** - Every deviation from upstream is recorded here
4. **Use submodules for VG features** - All custom code lives in forked submodules

---

## Architecture: Minimal Fork with Override Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UPSTREAM ODK CENTRAL                           │
├─────────────────────────────────────────────────────────────────────────┤
│  docker-compose.yml                                                    │
│  ├── server (upstream submodule)                                       │
│  ├── client (upstream submodule)                                       │
│  └── nginx (upstream image)                                            │
└─────────────────────────────────────────────────────────────────────────┘

                              ↓ MINIMAL FORK ↓

┌─────────────────────────────────────────────────────────────────────────┐
│                            VG FORK                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  docker-compose.yml (PURE UPSTREAM v2025.4.1) ✅                       │
│  ├── server → VG fork (drguptavivek/central-backend)                  │
│  ├── client → VG fork (drguptavivek/central-frontend)                 │
│  └── nginx → VG base image (with modsecurity)                         │
│                                                                        │
│  docker-compose.override.yml (VG SECURITY ONLY) ➕                     │
│  ├── Modsecurity/CRS configs                                          │
│  └── Security logging volumes                                          │
│                                                                        │
│                                                                        │
│  files/nginx/odk.conf.template (UPSTREAM + 6 LINES) ⚠️                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File-by-File Changes

### 1. docker-compose.yml

**Status:** ✅ PURE UPSTREAM (No VG modifications)

**Verification:**
```bash
git diff v2025.4.1 -- docker-compose.yml
# Output: (empty - no differences)
```

**Purpose:** Matches upstream ODK Central v2025.4.1 exactly

**Benefit:** When upstream releases v2025.5.0, just merge and resolve conflicts in .gitmodules

---

### 2. docker-compose.override.yml ➕ VG ONLY

**Status:** VG-EXCLUSIVE FILE (does not exist in upstream)

**Location:** `/docker-compose.override.yml`

**Purpose:** Contains ONLY security-related configurations (modsecurity, CRS)

**Structure:**
```yaml
services:
  nginx:
    build:
      args:
        NGINX_BASE_IMAGE: ${NGINX_BASE_IMAGE:-drguptavivek/central-nginx-vg-base:6.0.1}
    volumes:
      # VG modsecurity nginx configs
      - ./files/vg-nginx/vg-nginx-modules.conf:/etc/nginx/modules-enabled/50-vg-nginx-modules.conf:ro
      - ./files/vg-nginx/vg-modsecurity-odk.conf:/etc/modsecurity/modsecurity-odk.conf:ro
      - ./files/vg-nginx/vg-headers-more.conf:/usr/share/odk/nginx/vg-headers-more.conf:ro
      # Modsecurity CRS configs
      - ./crs/crs-setup.conf.example:/etc/modsecurity/crs/crs-setup.conf:ro
      - ./crs/rules:/etc/modsecurity/crs/rules:ro
      - ./crs_custom:/etc/modsecurity/custom:ro
      # Security logging
      - ./logs/nginx:/var/log/nginx
      - ./logs/modsecurity:/var/log/modsecurity
```

**Changes Made:**
| Service | Addition | Reason |
|---------|----------|--------|
| `nginx` | Custom base image build arg | Use nginx with modsecurity compiled |
| `nginx` | 3 volume mounts (vg-nginx configs) | Modsecurity configuration |
| `nginx` | 3 volume mounts (CRS rules) | OWASP CRS v4.21.0 |
| `nginx` | 2 volume mounts (logs) | Persistent audit logging |

**Note:** Uses default upstream network (no custom networks)

---


### 3. files/nginx/odk.conf.template ⚠️ MINIMAL CHANGE

**Status:** UPSTREAM + 6 LINES OF VG DIRECTIVES

**Location:** `/files/nginx/odk.conf.template`

**Diff:**
```diff
diff --git a/files/nginx/odk.conf.template b/files/nginx/odk.conf.template
index 6ab6e0c..2306c7b 100644
--- a/files/nginx/odk.conf.template
+++ b/files/nginx/odk.conf.template
@@ -104,6 +104,13 @@ server {

   server_tokens off;

+  # VG: Enable ModSecurity + OWASP CRS
+  modsecurity on;
+  modsecurity_rules_file /etc/modsecurity/modsecurity-odk.conf;
+
+  # VG: Hardening via headers-more
+  include /usr/share/odk/nginx/vg-headers-more.conf;
+
   add_header Content-Security-Policy-Report-Only "default-src 'none'; connect-src https://translate.google.com https://translate.googleapis.com; img-src https://translate.google.com; report-uri /csp-report";
   include /usr/share/odk/nginx/common-headers.conf;

@@ -172,6 +179,9 @@ server {
   }

   location ~ ^/v\d {
+    # VG: Disable CRS blocking rules for Central API (PATCH/PUT/DELETE methods)
+    modsecurity_rules 'SecRuleRemoveById 911100 949110 949111';
+
     proxy_hide_header Content-Security-Policy-Report-Only;
     add_header Content-Security-Policy-Report-Only "default-src 'none'; report-uri /csp-report";
```

**Lines Added:** 6 (lines 107-112, 182-183)

**Why This Can't Be Pure Upstream:**
Upstream doesn't use modsecurity. Pure upstream odk.conf.template has no modsecurity directives. These 6 lines are essential for the WAF to function.

**All Changes Are Marked:** Every VG addition starts with `# VG:` comment for easy identification

---

### 4. .gitmodules

**Status:** VG-MODIFIED (3 additional submodules)

**Location:** `/.gitmodules`

**Upstream Submodules:**
```ini
[submodule "server"]
    path = server
    url = https://github.com/getodk/central-backend.git
[submodule "client"]
    path = client
    url = https://github.com/getodk/central-frontend.git
```

**VG Submodules:**
```ini
[submodule "server"]
    path = server
    url = https://github.com/drguptavivek/central-backend.git
[submodule "client"]
    path = client
    url = https://github.com/drguptavivek/central-frontend.git
[submodule "agentic_kb"]
    path = agentic_kb
    url = https://github.com/drguptavivek/agentic_kb.git
[submodule "central-nginx-vg-base"]
    path = central-nginx-vg-base
    url = https://github.com/drguptavivek/central-nginx-vg-base.git
[submodule "crs"]
    path = crs
    url = https://github.com/coreruleset/coreruleset.git
```

**Changes:**
| Submodule | Upstream | VG | Purpose |
|-----------|----------|-----|---------|
| `server` | `getodk/central-backend` | `drguptavivek/central-backend` | VG: App user auth, IP rate limiting |
| `client` | `getodk/central-frontend` | `drguptavivek/central-frontend` | VG: UI customizations, QR codes |
| `agentic_kb` | ❌ None | ➕ Added | Cross-project knowledge base |
| `central-nginx-vg-base` | ❌ None | ➕ Added | Nginx with modsecurity |
| `crs` | ❌ None | ➕ Added | OWASP CRS v4.21.0 |

**Current Pointers:**
```
server  → 0f2a50a4 (vg-work with IP rate limiting)
client  → 405e431b (vg-work with UI customizations)
agentic_kb → 4c2a10be (main)
central-nginx-vg-base → 7f2993d8 (main)
crs → 2ac6c00a (v4.21.0)
```

---

## VG-Exclusive Files

### files/vg-nginx/ ➕ NEW DIRECTORY

**Purpose:** Modsecurity configuration files

| File | Description | Lines |
|------|-------------|-------|
| `vg-nginx-modules.conf` | Load modsecurity module | 3 |
| `vg-modsecurity-odk.conf` | Main modsecurity config (includes CRS) | 36 |
| `vg-headers-more.conf` | Security headers (HSTS, X-Frame-Options, etc.) | 8 |

### crs/ ➕ NEW SUBMODULE

**Repository:** `coreruleset/coreruleset`
**Version:** v4.21.0
**Tag:** `v4.21.0` (commit 2ac6c00a)

**Purpose:** OWASP Core Rule Set for Modsecurity

**Key Rules:**
- `REQUEST-911-METHOD-ENFORCEMENT.conf` → Rule 911100 (method enforcement)
- `REQUEST-942-APPLICATION-ATTACK-SQLI.conf` → Rule 942290 (SQLi detection)
- `REQUEST-949-BLOCKING-EVALUATION.conf` → Rules 949110, 949111 (blocking)

### crs_custom/ ➕ NEW DIRECTORY

**Purpose:** VG-specific CRS exclusions to prevent false positives

| File | Rule Disabled | Scope | Condition |
|------|--------------|-------|-----------|
| `00-empty.conf` | None | N/A | Placeholder |
| `10-odk-exclusions.conf` | 930130 (file access) | `/client-config.json` | Always |
| `20-odk-odata-exclusions.conf` | 942290, 920100 (SQLi) | `.svc/` OData endpoints | Session cookie |
| `30-odk-api-methods.conf` | 911100 (methods) | `/v1/` API | Session cookie |
| `40-odk-api-anomaly-threshold.conf` | Anomaly scoring | API endpoints | Adjusted thresholds |

### logs/ ➕ NEW DIRECTORY (Gitignored)

**Structure:**
```
logs/
├── nginx/
│   ├── access.log
│   └── error.log
└── modsecurity/
    └── audit.log (JSON format)
```

**Purpose:** Persistent audit trail for security monitoring

---

## Docker Stack Comparison

### Complete Docker Compose Files Comparison

| File | Upstream | VG | Auto-loaded? |
|------|----------|-----|--------------|
| `docker-compose.yml` | ✅ Exists | ✅ Pure upstream v2025.4.1 | ✅ Yes |
| `docker-compose.override.yml` | ❌ None | ✅ Security configs | ✅ Yes |
| `docker-compose.vg-dev.yml` | ✅ Exists | ✅ Same as upstream | ❌ Manual `-f` |

### Logging Comparison

| Log Type | Upstream | VG |
|----------|----------|-----|
| Nginx access | Container logs (local driver) | `./logs/nginx/access.log` (bind mount) |
| Nginx error | Container logs (local driver) | `./logs/nginx/error.log` (bind mount) |
| Modsecurity audit | ❌ None | `./logs/modsecurity/audit.log` (JSON format) |

---

## Services Comparison

### All Services (Same as Upstream)

| Service | Image/Build | VG Changes |
|---------|------------|------------|
| `postgres14` | `postgres14.dockerfile` | None ✅ |
| `postgres` | `postgres-upgrade.dockerfile` | None ✅ |
| `service` | `service.dockerfile` | None ✅ |
| `nginx` | `nginx.dockerfile` | + build arg, volumes |
| `pyxform` | `ghcr.io/getodk/pyxform-http:v4.2.0` | None ✅ |
| `enketo` | `enketo.dockerfile` | None ✅ |
| `enketo_redis_main` | `redis:7.4.7` | None ✅ |
| `enketo_redis_cache` | `redis:7.4.7` | None ✅ |
| `secrets` | `secrets.dockerfile` | None ✅ |
| `mail` | `registry.gitlab.com/egos-tech/smtp:1.1.5` | None ✅ |

### Volumes (Same as Upstream)

```yaml
volumes:
  secrets:        # Secrets storage
  postgres14:     # Main database
  enketo_redis_main:    # Enketo main storage
  enketo_redis_cache:   # Enketo cache
```

---

## Usage Comparison

### Startup Commands

```bash
# Upstream
docker compose up                              # Production only

# VG (Ours)
docker compose up                              # Production + security (auto-loaded)
docker compose -f docker-compose.yml \
               -f docker-compose.override.yml \
               -f docker-compose.vg-dev.yml up    # Full dev stack
```

### Verification Commands

```bash
# Verify pure upstream files
git diff v2025.4.1 -- docker-compose.yml
git diff v2025.4.1 -- docker-compose.vg-dev.yml
git diff v2025.4.1 -- files/nginx/setup-odk.sh

# Check VG modifications (only these should show diffs)
git diff v2025.4.1 -- files/nginx/odk.conf.template
git diff v2025.4.1 -- .gitmodules

# List VG-exclusive files
git ls-files --others --exclude-standard | grep -E "^(files/vg-nginx|crs_custom)/"
```

---

## Future Upstream Updates

### Updating to v2025.5.0 (Example)

```bash
# 1. Fetch and merge
git fetch upstream --tags
git merge v2025.5.0

# 2. Resolve conflicts (keep VG versions)
git checkout --ours .gitmodules        # Keep VG submodule pointers
git checkout --ours files/nginx/odk.conf.template  # Keep VG modsecurity lines
git checkout --theirs docker-compose.yml  # Take upstream (should be no conflicts)
git checkout --theirs files/nginx/setup-odk.sh  # Take upstream

# 3. Review and commit
git add -A
git commit -m "Merge: upstream v2025.5.0"
git push origin vg-work
```

**Expected Conflicts:**
- `.gitmodules` - Always keep VG version (points to your repos)
- `files/nginx/odk.conf.template` - Keep VG modsecurity lines
- `docs/vg/` - Keep VG documentation

**Should Merge Cleanly:**
- `docker-compose.yml` - Pure upstream, should have no conflicts
- `docker-compose.vg-dev.yml` - Same as upstream
- `files/nginx/setup-odk.sh` - Pure upstream

---

## Summary Table

| Category | Upstream | VG | Count |
|----------|----------|-----|-------|
| **Docker compose files** | 2 | 3 (+1) | +1 file |
| **Submodules** | 2 | 5 (+3) | +3 submodules |
| **Networks** | 1 (default) | 1 (default) | 0 (uses upstream) |
| **Nginx config changes** | Pure upstream | 6 lines | 6 lines |
| **VG config directories** | 0 | 2 | +2 dirs |
| **VG config files** | 0 | 8 | +8 files |

---

## Key Principles

### 1. Pure Upstream Base ✅
- `docker-compose.yml` matches upstream exactly
- `docker-compose.vg-dev.yml` matches upstream exactly
- `files/nginx/setup-odk.sh` matches upstream exactly

### 2. Isolated Security Layer ➕
- `docker-compose.override.yml` contains ONLY modsecurity/CRS configs
- No development tools in override file
- Easy to disable security for testing

### 3. Minimal Nginx Changes ⚠️
- Only 6 lines added to `odk.conf.template`
- All marked with `# VG:` comments
- Essential for modsecurity to function

### 4. Modular VG Features 📦
- All VG code in submodules (server, client)
- Security configs in separate override file
- Documentation in `docs/vg/`

### 5. Future-Proof Architecture 🚀
- Upstream merges are trivial
- Clear separation of concerns
- Easy to identify what's custom vs upstream

---

## Related Documentation

- **Modsecurity Implementation:** `docs/vg/vg_modsecurity.md`
- **Integration Plan:** `docs/vg/central-rebase-v2025.4.0/plan.md`
- **Checkpoint:** `CHECKPOINT-2026-01-13-v2025.4.1-integration.md`
- **VG Server Edits:** `docs/vg/vg-server/vg_core_server_edits.md`
- **VG Client Edits:** `docs/vg/vg-client/vg_core_client_edits.md`

---

## Change History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-13 | v2025.4.1 | Initial integration with minimal fork architecture |
| 2026-01-14 | v2025.4.1 | Added comprehensive docker stack comparison |

---

## Verification Checklist

Before committing any changes to this meta-repo, verify:

- [ ] `docker-compose.yml` matches upstream exactly
- [ ] `docker-compose.vg-dev.yml` matches upstream exactly
- [ ] `files/nginx/setup-odk.sh` matches upstream exactly
- [ ] `files/nginx/odk.conf.template` has only 6 VG lines (marked with `# VG:`)
- [ ] `.gitmodules` points to VG repos
- [ ] All VG changes are documented in this file
- [ ] All VG changes are documented in `docs/vg/`

**Remember:** If you're modifying an upstream core file, ask yourself:
1. Is this absolutely necessary?
2. Can it be done in a submodule instead?
3. Can it be done in docker-compose.override.yml instead?
4. Is it documented here?
