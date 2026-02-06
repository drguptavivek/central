# Nginx In-Container Logrotate (VG)

## Why this exists

Nginx access/error logs are written to `/var/log/nginx` (bind-mounted to `./logs/nginx`).
Docker logging options rotate container stdout/stderr logs, but do not rotate these nginx log files.

This setup adds in-container rotation for:

- `/var/log/nginx/*.log`
- `/var/log/modsecurity/*.log`

without modifying upstream `files/nginx/setup-odk.sh`.

## Implementation

### Files

- `files/nginx/logrotate-nginx.conf`
- `files/nginx/start-with-logrotate.sh`

### Dockerfile wiring

`nginx.dockerfile`:

- Installs `logrotate`
- Copies `files/nginx/logrotate-nginx.conf` to `/etc/logrotate.d/nginx-container`
- Copies `files/nginx/start-with-logrotate.sh` to `/scripts/`
- Uses `ENTRYPOINT ["/scripts/start-with-logrotate.sh"]`

### Runtime behavior

`/scripts/start-with-logrotate.sh`:

1. Starts a background loop
2. Runs:
   - `logrotate -s /var/lib/logrotate/status /etc/logrotate.d/nginx-container`
3. Sleeps `86400` seconds (daily)
4. Repeats
5. `exec /scripts/setup-odk.sh`

## Rotation policy

`files/nginx/logrotate-nginx.conf`:

- `daily`
- `rotate 270`
- `maxsize 50M`
- `compress`
- `delaycompress`
- `copytruncate`

## Apply changes

Rebuild and recreate nginx:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml up -d --build --force-recreate nginx
```
