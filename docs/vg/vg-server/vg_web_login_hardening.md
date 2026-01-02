# VG: Web user login hardening

> **Last Updated**: 2026-01-01

Scope: `/v1/sessions` (web user login).

## Behavior
- Failed login attempts are audited with normalized email, IP, and user agent.
- Login lockout: 5 failed attempts within 5 minutes per `email+IP` trigger a 10-minute lockout.
- Timing normalization: missing-email and bad-password both run a bcrypt compare.

## Audit actions
- `user.session.create.failure`
- `user.session.lockout`

## Tests
```
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-webusers.js'
```
