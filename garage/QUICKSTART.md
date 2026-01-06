# Garage S3 Quickstart (5 Minutes)

**Single-bucket, HTTP-01 certificate-friendly setup.**

---

## Why This Setup is Simple

✅ **One bucket** (`odk-central`) → specific subdomain (`odk-central.s3.central.local`)
✅ **HTTP-01 challenge** works for Let's Encrypt (no DNS-01 needed)
✅ **No wildcard certificates** required
✅ **Two endpoints**: S3 API + Web UI

---

## 1. Generate Configs (Init)

```bash
# From ODK Central root directory
./scripts/init-odk.sh
```

Select:
- **S3 blob storage**: `Garage (local S3 - optional)`

This generates:
- `.env` (sets `VG_GARAGE_ENABLED=true`, `S3_SERVER`, `S3_BUCKET_NAME`, and empty `S3_ACCESS_KEY/S3_SECRET_KEY`)
- `garage/garage.toml` (gitignored; contains `rpc_secret`)
- `garage/storage.conf` (capacity for layout)
- `docker-compose-garage.yml` (overlay)

---

## 2. Start Garage + Bootstrap Bucket/Key

```bash
# Start Garage only
docker compose -f docker-compose.yml -f docker-compose-garage.yml up -d garage

# Bootstrap (configures layout, creates bucket/key, updates .env)
./scripts/add-s3.sh
```

---

## 3. Configure DNS/Hosts

### For Local Development (self-signed SSL):

Add to `/etc/hosts`:
```
127.0.0.1  central.local
127.0.0.1  odk-central.s3.central.local
127.0.0.1  web.central.local
```

### For Production:

**DNS A Records:**
```
central.local                    → your-server-ip
odk-central.s3.central.local     → your-server-ip
web.central.local                → your-server-ip
```

**Let's Encrypt Certificate (HTTP-01):**
```bash
# Add to EXTRA_SERVER_NAME in .env
EXTRA_SERVER_NAME=odk-central.s3.central.local web.central.local

# Let's Encrypt will use HTTP-01 challenge (simpler than DNS-01!)
# Certificate will cover:
#   - central.local
#   - odk-central.s3.central.local
#   - web.central.local
```

---

## 4. Verify Setup

**Check environment:**
```bash
grep ^S3_ .env
```

**Check Garage status:**
```bash
docker exec odk-garage /garage status
docker exec odk-garage /garage bucket info odk-central
```

**Check nginx config:**
```bash
docker compose exec nginx sh -lc 'grep "server_name\\|proxy_pass" /etc/nginx/conf.d/s3.conf'
```

**Test connectivity:**
```bash
# From inside service container
docker compose exec service sh -c 'curl -I http://garage:3900/ 2>&1 | head -3'
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Client Request                                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
    https://odk-central.s3.        https://web.
    central.local                  central.local
         │                             │
┌────────▼─────────────────────────────▼────────────────────┐
│  Nginx (/etc/nginx/conf.d/s3.conf)                        │
│                                                            │
│  Block 1: odk-central.s3.central.local → garage:3900     │
│           (S3 API - bucket-specific)                      │
│                                                            │
│  Block 2: web.central.local → garage:3903                │
│           (Web UI - shared interface)                     │
└────────┬───────────────────────────┬─────────────────────┘
         │                           │
         └──────────┬────────────────┘
                    │ Docker network: central_default
         ┌──────────▼──────────┐
         │  odk-garage         │
         │  Port 3900: S3 API  │
         │  Port 3903: Web UI  │
         └─────────────────────┘
```

---

## Key Configuration Files

### `garage/garage.toml`
```toml
[s3_api]
  s3_region = "garage"
  api_bind_addr = "[::]:3900"
  root_domain = ".s3.central.local"

[s3_web]
  bind_addr = "[::]:3903"
  root_domain = ".web.central.local"
```

### `/etc/nginx/conf.d/s3.conf` (generated inside nginx container)
```nginx
# S3 API (bucket-specific: no wildcard)
server {
  listen 443 ssl;
  server_name odk-central.s3.central.local s3.central.local;
  location / {
    proxy_pass http://garage:3900;
  }
}

# S3 Web UI (shared)
server {
  listen 443 ssl;
  server_name web.central.local;
  location / {
    proxy_pass http://garage:3903;
  }
}
```

### `.env` (S3 variables added)
```bash
S3_SERVER=https://odk-central.s3.central.local
S3_ACCESS_KEY=GK...
S3_SECRET_KEY=...
S3_BUCKET_NAME=odk-central
```

---

## Troubleshooting

### s3.conf not found
```bash
docker compose exec nginx sh -lc 'ls -la /etc/nginx/conf.d/s3.conf && head -n 5 /etc/nginx/conf.d/s3.conf'
```

### Garage not running
```bash
docker compose -f docker-compose.yml -f docker-compose-garage.yml logs garage
docker compose -f docker-compose.yml -f docker-compose-garage.yml restart garage
```

### Service can't reach Garage
```bash
# Check both on same network
docker inspect odk-garage central-service-1 --format '{{.Name}}: {{range $net, $conf := .NetworkSettings.Networks}}{{$net}} {{end}}'

# Test connectivity
docker compose exec service nc -zv garage 3900
```

### S3 credentials not loaded
```bash
# Check if env vars passed to service
docker compose config | grep -A 5 "S3_"

# Restart service after .env changes
docker compose restart service
```

### Apply `.env` changes
```bash
docker compose restart service nginx
```

---

## Testing S3 Integration

### Create test submission with attachment

ODK Service will automatically use S3 for blob storage when configured.

### Watch logs:
```bash
docker compose logs -f service | grep -i s3
```

### Check bucket contents:
```bash
docker exec odk-garage /garage bucket info odk-central
# Shows: Size, Objects count
```

---

## Why Bucket-Specific (Not Wildcard)?

| Approach | Certificate | Pros | Cons |
|----------|-------------|------|------|
| **Bucket-specific** (this setup) | HTTP-01 (simple) | ✅ Simple Let's Encrypt<br>✅ No DNS provider integration needed<br>✅ Works with most setups | Only supports one bucket |
| **Wildcard** (`*.s3.domain`) | DNS-01 (complex) | Supports many buckets | ❌ Requires DNS provider API<br>❌ More complex setup |

**For ODK Central:** Only ONE bucket is used (`odk-central`), so bucket-specific is simpler!

---

## Next Steps

1. **Test upload**: Create submission with photo attachment
2. **Monitor logs**: `docker compose logs -f service | grep -i s3`
3. **Check storage**: `docker exec odk-garage /garage bucket info odk-central`

---

## Full Documentation

- **Garage docs**: https://garagehq.deuxfleurs.fr/
- **Scripts**: `./scripts/init-odk.sh` and `./scripts/add-s3.sh`

---

**Tip:** Re-running `./scripts/add-s3.sh` is safe; it reuses existing credentials when possible.
