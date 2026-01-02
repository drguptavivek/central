# Custom nginx base image (VG)

Central’s `nginx.dockerfile` can be built on top of a drop-in nginx base image
that already includes:

- ModSecurity v3 + the `ngx_http_modsecurity_module` dynamic module
- `headers-more` (`ngx_http_headers_more_filter_module`) for response header hardening
- OWASP CRS baked into the base image (can be overridden with a bind mount)

Base image repository:
`central-nginx-vg-base/` (submodule) and `drguptavivek/central-nginx-vg-base:*`

## Using the base image in Central

Central’s nginx build uses this build arg (see `nginx.dockerfile`):

- `NGINX_BASE_IMAGE` (defaults to `drguptavivek/central-nginx-vg-base:6.0.1`)

You can override it via env var when running compose:

```bash
NGINX_BASE_IMAGE=drguptavivek/central-nginx-vg-base:6.0.1 docker compose build nginx
```

## Enabling ModSecurity + CRS

`files/nginx/odk.conf.template` enables ModSecurity for the main HTTPS server:

- `modsecurity on;`
- `modsecurity_rules_file /etc/modsecurity/modsecurity-odk.conf;`

The base image includes:

- `/etc/modsecurity/modsecurity.conf-recommended`
- `/etc/modsecurity/unicode.mapping`
- CRS at `/etc/modsecurity/crs/...`

### Local CRS override (bind mount)

To test CRS changes locally without rebuilding images, bind mount your CRS dir
over `/etc/modsecurity/crs`:

- Add CRS as a git submodule at `./crs` (official repo, pinned tag), or use any local path
- Uncomment/add this volume in `docker-compose.yml` under the `nginx` service:

```yaml
- ./crs:/etc/modsecurity/crs:ro
```

## Custom ModSecurity rules / exclusions

Put any local rules/exclusions in `./crs_custom/` (kept separate from the CRS submodule),
and they will be loaded automatically:

- Host: `./crs_custom/*.conf`
- Container: `/etc/modsecurity/custom/*.conf`

`docker-compose.yml` mounts this by default:

```yaml
- ./crs_custom:/etc/modsecurity/custom:ro
```

Typical usage:

- `crs_custom/10-exclusions.conf` (false-positive exclusions using `SecRuleRemoveById` or `ctl:ruleRemoveById`)
- `crs_custom/20-local-rules.conf` (site-specific allow/deny rules)

## Logging (portable across macOS/Windows/Linux)

`files/nginx/odk.conf.template` writes nginx logs to both stdio and files:

- nginx access: `/dev/stdout` and `/var/log/nginx/access.log`
- nginx error:  `/dev/stderr` and `/var/log/nginx/error.log`

`files/nginx/vg-modsecurity-odk.conf` writes ModSecurity audit logs to:

- `/var/log/modsecurity/audit.log` (JSON)

`docker-compose.yml` mounts these paths so they persist on the host:

- `./logs/nginx:/var/log/nginx`
- `./logs/modsecurity:/var/log/modsecurity`

## Header hardening

`files/nginx/odk.conf.template` includes `files/nginx/vg-headers-more.conf` to
remove common identity/leak headers (for example `Server` and `X-Powered-By`).
