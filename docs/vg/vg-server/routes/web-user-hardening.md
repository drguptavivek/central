# Web user login hardening

Scope: `/v1/sessions` (web user login).

## Goals
- Rate-limit failed logins to slow brute-force attempts.
- Audit failed logins without confirming account existence.
- Normalize timing between missing-email and bad-password responses.

## Behavior
- Failure audits: each auth failure logs `user.session.create.failure` with:
  - `email` (normalized to lowercase)
  - `ip` (string or null)
  - `userAgent` (string or null)
- Lockout: 5 failed attempts within 5 minutes per `email+IP` triggers a 10-minute lock.
  - Lockout event: `user.session.lockout` with `email`, `ip`, `durationMinutes: 10`.
  - While locked, `/v1/sessions` returns the same 401 as other auth failures.
- Timing normalization:
  - If email is missing, server still runs a bcrypt compare using any existing user hash.
  - Response remains 401 with standard auth error message.

## API responses

### Failed login (wrong password or unknown email)
```
HTTP/1.1 401 Unauthorized
X-Login-Attempts-Remaining: <count>
{
  "code": 401.2,
  "message": "Could not authenticate with the provided credentials."
}
```

### Locked out
```
HTTP/1.1 401 Unauthorized
Retry-After: <seconds>
{
  "code": 401.2,
  "message": "Could not authenticate with the provided credentials."
}
```

## Data sources
- Audit-based tracking:
  - Failure counts are computed from recent `user.session.create.failure` audits.
  - Lockouts are computed from recent `user.session.lockout` audits.
- No new tables are introduced for web-user lockouts.

## Settings
- `vg_web_user_lock_duration_minutes` (system-level): lockout duration in minutes (default 10).

## Tests
```
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-webusers.js'
```
