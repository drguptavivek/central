---
title: VG Central — Quick Install Guide
type: howto
domain: ODK-Central-vg
tags:
  - installation
  - docker
  - quick-start
  - deployment
status: approved
created: 2026-03-29
updated: 2026-03-29
---

# VG Central — Quick Install Guide

Production install of the VG fork on a Linux server with Docker.

## Prerequisites

- Docker + Docker Compose v2
- A domain name pointing to the server (or `central.local` for local testing)
- Ports 80 and 443 open (for Let's Encrypt) or 443 only (for `customssl`/`upstream`)

## 1. Clone the repo

```bash
git clone https://github.com/drguptavivek/central.git
cd central
git submodule update --init --recursive
```

## 2. Configure environment

```bash
cp .env.template .env
```

Edit `.env`:

```env
DOMAIN=odk.yourdomain.com
SYSADMIN_EMAIL=admin@yourdomain.com
SSL_TYPE=letsencrypt     # letsencrypt | selfsign | customssl | upstream
```

**SSL_TYPE options:**

| Value | When to use |
|---|---|
| `letsencrypt` | Public domain, ports 80+443 open |
| `selfsign` | Local/dev, no real domain |
| `customssl` | You supply your own certs |
| `upstream` | Behind a reverse proxy/LB that handles TLS |

## 3. Start the stack

```bash
make prod
```

This runs `docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-prod.yml up -d`.

VG DB schema migrations run automatically when the `service` container starts.

## 4. Create the admin user

```bash
docker compose exec service odk-cmd --email admin@yourdomain.com user-create
docker compose exec service odk-cmd --email admin@yourdomain.com user-promote
```

## 5. Verify

```bash
# Check all containers are up
docker compose ps

# Tail logs
make prod-logs

# Smoke test
curl -kI "https://${DOMAIN}/version.txt"
```

Browse to `https://<DOMAIN>` and log in with the admin credentials.

## Local testing (no real domain)

```bash
# Add to /etc/hosts:
echo "127.0.0.1 central.local" | sudo tee -a /etc/hosts

# In .env:
DOMAIN=central.local
SSL_TYPE=selfsign
```

## See also

- [docker-deployment.md](docker-deployment.md) — compose file architecture
- [docker-development.md](docker-development.md) — local dev with HMR
- [vg-server/vg_installation.md](vg-server/vg_installation.md) — full installation reference
