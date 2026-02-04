# VG: Password reset hardening

> **Last Updated**: 2026-02-04

Scope: `/v1/users/reset/initiate`.

## Behavior
- Every reset-initiate attempt is audited with normalized email, IP, and user agent.
- IP lockout: 3 attempts within 10 minutes → 30-minute lockout.
- Email lockout: 3 attempts within 30 minutes → 60-minute lockout.
- Locked requests return 429 (no retryAfterSeconds in response).
- Non-locked responses remain 200 to avoid user enumeration.

## Audit actions
- `user.reset.initiate`
- `user.reset.ip.lockout`
- `user.reset.email.lockout`

## Tests
```
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-user-reset-rate-limit.js'
```
