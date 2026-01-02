# Docker deployment (VG)

> **Last Updated**: 2026-01-02

This doc captures the “standard” docker deployment shape for this `central` meta repo.

## Images

- `service`: Central backend API (Node.js)
- `nginx`: TLS termination + static frontend + reverse proxy to `service` (+ optional dev proxy to `client-dev`)
- `postgres14`, `enketo`, etc. as defined by compose

## Build

```bash
docker compose build service nginx
```

If you are deploying using prebuilt images, replace `build:` with `image:` tags in your deployment compose file(s) and push/pull via your registry of choice.

## Bring up

```bash
docker compose up -d
docker compose ps
```

## TLS modes

TLS behavior is controlled by environment and the `nginx` entrypoint script (`files/nginx/setup-odk.sh`), which renders templates into `/etc/nginx/conf.d/`.

Common patterns:

- `SSL_TYPE=letsencrypt`: certbot flow (ACME HTTP-01)
- `SSL_TYPE=selfsign`: local self-signed certs
- `SSL_TYPE=customssl`: mount your own certs into the expected path
- `SSL_TYPE=upstream`: run nginx on plain HTTP behind an upstream TLS proxy/LB

## Health checks / smoke tests

```bash
docker compose logs -f --tail=100 nginx service
curl -kI "https://${DOMAIN}/version.txt"
```
