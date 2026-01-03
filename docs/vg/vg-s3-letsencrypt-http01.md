# Garage S3 with Let's Encrypt (HTTP-01 Challenge)

**How to configure Let's Encrypt certificates for Garage S3 using HTTP-01 challenge.**

---

## Why HTTP-01 Works with This Setup

✅ **Bucket-specific subdomain** (`odk-central.s3.central.local`)
✅ **No wildcard certificate** needed
✅ **Standard HTTP-01 challenge** (simpler than DNS-01)

### Comparison: HTTP-01 vs DNS-01

| Challenge Type | When to Use | Complexity | Requirements |
|----------------|-------------|------------|--------------|
| **HTTP-01** (this guide) | Single bucket, specific subdomain | ⭐ Simple | Port 80 accessible |
| **DNS-01** | Multiple buckets, wildcard cert | ⭐⭐⭐ Complex | DNS provider API |

**For ODK Central:** One bucket (`odk-central`) → HTTP-01 is perfect!

---

## Prerequisites

1. **ODK Central** with Garage S3 setup complete
2. **Domain name** pointing to your server
3. **Port 80 and 443** accessible from internet
4. **DNS A records** configured (see below)

---

## DNS Configuration

Add these A records to your DNS provider:

```dns
# Main ODK Central domain
central.example.com              → your-server-ip

# S3 API endpoint (bucket-specific)
odk-central.s3.central.example.com → your-server-ip

# S3 Web UI
web.central.example.com          → your-server-ip
```

**Wait for DNS propagation** (check with `dig` or `nslookup`):
```bash
dig +short central.example.com
dig +short odk-central.s3.central.example.com
dig +short web.central.example.com
# All should return: your-server-ip
```

---

## Step 1: Update `.env` for Let's Encrypt

Edit `.env` file:

```bash
# Domain (replace with your domain)
DOMAIN=central.example.com

# SSL Type: Let's Encrypt
SSL_TYPE=letsencrypt

# Email for Let's Encrypt notifications
SYSADMIN_EMAIL=admin@example.com

# Add S3 subdomains to EXTRA_SERVER_NAME
EXTRA_SERVER_NAME=odk-central.s3.central.example.com web.central.example.com

# S3 configuration (already set by Garage setup)
S3_SERVER=https://s3.central.example.com
S3_ACCESS_KEY=GK...
S3_SECRET_KEY=...
S3_BUCKET_NAME=odk-central
```

**Key points:**
- `SSL_TYPE=letsencrypt` enables Let's Encrypt
- `EXTRA_SERVER_NAME` adds S3 subdomains to certificate
- Let's Encrypt will issue **one certificate** covering all three domains

---

## Step 2: Regenerate S3 Nginx Config

Update nginx S3 config with new domain:

```bash
bash scripts/generate-s3-conf.sh
```

**Output:**
```
✓ Generated files/nginx/s3.conf
  DOMAIN=central.example.com
  SSL_TYPE=letsencrypt
  CERT_DOMAIN=central.example.com
  S3_BUCKET_NAME=odk-central

S3 API endpoint: odk-central.s3.central.example.com
S3 Web UI:       web.central.example.com

Restart nginx to apply:
  docker compose restart nginx
```

**Verify s3.conf:**
```bash
grep "server_name\|ssl_certificate" files/nginx/s3.conf
```

Should show:
```nginx
server_name odk-central.s3.central.example.com s3.central.example.com;
ssl_certificate /etc/letsencrypt/live/central.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/central.example.com/privkey.pem;
```

---

## Step 3: Restart ODK Services

Restart nginx and service to pick up new configuration:

```bash
docker compose restart nginx service
```

**Check nginx is healthy:**
```bash
docker compose ps nginx
# Status should show: Up X seconds (healthy)
```

---

## Step 4: Verify Let's Encrypt Certificate

Let's Encrypt will automatically issue a certificate covering:
1. `central.example.com`
2. `odk-central.s3.central.example.com`
3. `web.central.example.com`

**Check certificate:**
```bash
# From outside the server
curl -vI https://odk-central.s3.central.example.com 2>&1 | grep -A 5 "SSL certificate"

# Or use openssl
openssl s_client -connect odk-central.s3.central.example.com:443 -servername odk-central.s3.central.example.com < /dev/null 2>/dev/null | openssl x509 -noout -text | grep -A 2 "Subject Alternative Name"
```

**Expected output:**
```
Subject Alternative Name:
    DNS:central.example.com
    DNS:odk-central.s3.central.example.com
    DNS:web.central.example.com
```

---

## Step 5: Test S3 Connectivity

**Test S3 API endpoint:**
```bash
curl -I https://odk-central.s3.central.example.com/
# Should return HTTP 403 Forbidden (expected - no auth provided)
# NOT nginx error or certificate error
```

**Test S3 Web UI:**
```bash
curl https://web.central.example.com/
# Should return Garage web interface HTML
```

---

## How HTTP-01 Challenge Works

When Let's Encrypt issues/renews certificates:

1. **Challenge Request**: Let's Encrypt sends HTTP request to:
   ```
   http://central.example.com/.well-known/acme-challenge/TOKEN
   http://odk-central.s3.central.example.com/.well-known/acme-challenge/TOKEN
   http://web.central.example.com/.well-known/acme-challenge/TOKEN
   ```

2. **ODK Nginx** handles challenge (via `certbot` or ACME client)

3. **Validation**: Let's Encrypt verifies response

4. **Certificate Issued**: Covers all domains in `EXTRA_SERVER_NAME`

**Port 80 must be accessible** from the internet for HTTP-01 to work!

---

## Certificate Renewal

Let's Encrypt certificates expire every **90 days**.

**ODK Central auto-renews** via cron or systemd timer (depending on installation).

**Manual renewal test:**
```bash
# Dry-run (test without actual renewal)
docker compose exec nginx certbot renew --dry-run

# Force renewal
docker compose exec nginx certbot renew --force-renewal
```

**Check renewal logs:**
```bash
docker compose logs nginx | grep -i certbot
```

---

## Troubleshooting

### Certificate doesn't include S3 subdomains

**Problem:** `EXTRA_SERVER_NAME` not set before certificate issuance.

**Solution:**
1. Add to `.env`: `EXTRA_SERVER_NAME=odk-central.s3.central.example.com web.central.example.com`
2. Force certificate renewal:
   ```bash
   docker compose exec nginx certbot renew --force-renewal
   docker compose restart nginx
   ```

### HTTP-01 challenge fails

**Problem:** Port 80 not accessible from internet.

**Check firewall:**
```bash
# From external machine
curl -I http://central.example.com/.well-known/acme-challenge/test
# Should NOT timeout or connection refused
```

**Solution:** Open port 80 in firewall/security group.

### "DNS problem: NXDOMAIN" error

**Problem:** DNS not configured or not propagated.

**Solution:**
1. Verify DNS records exist
2. Wait for propagation (up to 48 hours, usually faster)
3. Check with: `dig +short odk-central.s3.central.example.com`

### nginx fails to start after SSL changes

**Problem:** Invalid s3.conf or certificate paths.

**Check nginx config:**
```bash
docker compose exec nginx nginx -t
```

**Check logs:**
```bash
docker compose logs nginx --tail 50
```

---

## Migration from Self-Signed to Let's Encrypt

If you're migrating from self-signed certificates:

1. **Update .env:**
   ```bash
   # Change from:
   SSL_TYPE=selfsign

   # To:
   SSL_TYPE=letsencrypt
   EXTRA_SERVER_NAME=odk-central.s3.central.example.com web.central.example.com
   ```

2. **Regenerate configs:**
   ```bash
   bash scripts/generate-s3-conf.sh
   ```

3. **Restart services:**
   ```bash
   docker compose restart nginx service
   ```

4. **Verify certificate:**
   ```bash
   curl -vI https://odk-central.s3.central.example.com 2>&1 | grep "issuer"
   # Should show: CN=R3 (Let's Encrypt)
   ```

---

## Security Best Practices

✅ **Enable HSTS** (already configured in ODK nginx)
✅ **Use strong ciphers** (configured in s3.conf.template)
✅ **Auto-renewal** enabled (Let's Encrypt cron)
✅ **Monitor expiration** (Let's Encrypt sends email alerts)

---

## Alternative: DNS-01 Challenge

If you need **wildcard certificates** (e.g., `*.s3.central.example.com`):

**When to use:**
- Multiple S3 buckets with different names
- Dynamic bucket creation

**Requirements:**
- DNS provider API access (Cloudflare, Route53, etc.)
- DNS plugin for certbot
- More complex setup

**ODK Central users:** Stick with HTTP-01 (simpler!) since only one bucket is used.

---

## Related Documentation

- **Garage S3 Quickstart**: `garage/QUICKSTART.md`
- **Garage Setup Guide**: `garage/README-GARAGE-SETUP.md`
- **Let's Encrypt Docs**: https://letsencrypt.org/docs/challenge-types/
- **ODK Central SSL**: https://docs.getodk.org/central-install-digital-ocean/#ssl-certificate

---

## Summary

**HTTP-01 Challenge for Garage S3:**

1. Configure DNS A records (3 domains)
2. Set `SSL_TYPE=letsencrypt` and `EXTRA_SERVER_NAME` in `.env`
3. Regenerate s3.conf: `bash scripts/generate-s3-conf.sh`
4. Restart services: `docker compose restart nginx service`
5. Verify certificate covers all 3 domains

**Result:** Single Let's Encrypt certificate covering:
- `central.example.com` (ODK Central)
- `odk-central.s3.central.example.com` (S3 API)
- `web.central.example.com` (S3 Web UI)

🔒 **Secure, automated, free SSL for Garage S3!**
