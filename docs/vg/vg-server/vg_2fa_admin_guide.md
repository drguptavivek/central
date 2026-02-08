# VG: Two-Factor Authentication (2FA) Admin Guide

**Last Updated**: 2026-02-08
**Status**: ✅ Production Ready

---

## Overview

This guide covers administrative operations for TOTP-based Two-Factor Authentication (2FA) in ODK Central. It includes setup, configuration, user management, and emergency procedures to prevent admin lockout.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Configuration](#configuration)
4. [User Management](#user-management)
5. [Monitoring & Auditing](#monitoring--auditing)
6. [Emergency Procedures](#emergency-procedures)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Enable 2FA for Your Account

1. **Log in** to ODK Central
2. Navigate to **Account Settings** (top right menu)
3. Click the **Two-Factor Authentication** panel
4. Click **Enable 2FA**
5. **Scan the QR code** with Google Authenticator, Microsoft Authenticator, Authy, or similar
6. **Enter the 6-digit code** from your authenticator app
7. **Save backup codes** in a secure location (password manager recommended)
8. **Confirm** you've saved the codes

### Make 2FA Mandatory

To enforce 2FA for all web users, set the global flag:

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk -c \
  "UPDATE vg_settings SET vg_key_value = 'true' WHERE vg_key_name = 'vg_totp_required_web_users';"
```

**Note**: This will NOT lock out users who already have 2FA enabled. New users or those without 2FA will be prompted to enable it on next login.

---

## Prerequisites

### Database Setup

The TOTP tables are automatically created during migration:

```bash
# During initial deployment (runs automatically)
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql
```

### Required Settings Table Entries

```sql
-- These are automatically seeded with sensible defaults:
SELECT * FROM vg_settings WHERE vg_key_name LIKE '%totp%';

-- Expected rows:
-- vg_totp_required_web_users: false (set to 'true' to enforce 2FA)
-- vg_web_user_lock_duration_minutes: 10 (lockout duration after failed attempts)
-- vg_web_user_lock_window_minutes: 5 (time window for counting failures)
-- vg_web_user_lock_max_failures: 5 (max failed attempts before lockout)
```

---

## Configuration

### Global Settings

#### Make 2FA Mandatory for All Web Users

```bash
# Enable mandatory 2FA
docker exec -it central-postgres14-1 psql -U odk -d odk -c \
  "UPDATE vg_settings SET vg_key_value = 'true' WHERE vg_key_name = 'vg_totp_required_web_users';"

# Disable mandatory 2FA
docker exec -it central-postgres14-1 psql -U odk -d odk -c \
  "UPDATE vg_settings SET vg_key_value = 'false' WHERE vg_key_name = 'vg_totp_required_web_users';"

# Check current status
docker exec -it central-postgres14-1 psql -U odk -d odk -c \
  "SELECT vg_key_value FROM vg_settings WHERE vg_key_name = 'vg_totp_required_web_users';"
```

#### Adjust Login Lockout Settings

```bash
# Lockout duration (minutes) - default 10
docker exec -it central-postgres14-1 psql -U odk -d odk -c \
  "UPDATE vg_settings SET vg_key_value = '20' WHERE vg_key_name = 'vg_web_user_lock_duration_minutes';"

# Time window for counting failures (minutes) - default 5
docker exec -it central-postgres14-1 psql -U odk -d odk -c \
  "UPDATE vg_settings SET vg_key_value = '10' WHERE vg_key_name = 'vg_web_user_lock_window_minutes';"

# Max failures before lockout - default 5
docker exec -it central-postgres14-1 psql -U odk -d odk -c \
  "UPDATE vg_settings SET vg_key_value = '3' WHERE vg_key_name = 'vg_web_user_lock_max_failures';"
```

---

## User Management

### View User 2FA Status

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Check if a specific user has 2FA enabled
SELECT u.email, t.user_id, t.enabled, t.last_enabled_at
FROM users u
LEFT JOIN vg_user_totp t ON u.id = t.user_id
WHERE u.email = 'admin@example.com';
EOF
```

### List All Users with 2FA Enabled

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
SELECT u.email, t.enabled, t.last_enabled_at
FROM users u
JOIN vg_user_totp t ON u.id = t.user_id
WHERE t.enabled = true
ORDER BY t.last_enabled_at DESC;
EOF
```

### Disable 2FA for a User (Emergency)

**Use case**: User lost authenticator app and backup codes, or account is locked out.

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
BEGIN;

-- Find user
SELECT id, email FROM users WHERE email = 'admin@example.com';

-- Disable TOTP (replace <user_id> with actual ID)
DELETE FROM vg_user_totp WHERE user_id = <user_id>;

-- Clear any session locks (optional)
DELETE FROM sessions WHERE user_id = <user_id>;

-- Verify
SELECT * FROM vg_user_totp WHERE user_id = <user_id>;

COMMIT;
EOF
```

**After this operation:**
- User can log in without 2FA
- Next login will prompt to re-enable 2FA (if mandatory)
- Document the action in your incident log with timestamp and reason

### Generate New Backup Codes for a User

If a user lost their backup codes but still has access to their authenticator app:

1. Have them log in to their account
2. Navigate to **Account Settings** → **Two-Factor Authentication**
3. Click **Regenerate Backup Codes**
4. Enter their password
5. Save the new codes

(To do this for a user without their involvement, you would need to implement a backend endpoint - currently not available)

---

## Monitoring & Auditing

### Check Failed Login Attempts

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Last 20 failed login attempts (last 1 hour)
SELECT created_at, action, details
FROM audits
WHERE action IN ('user.session.create.failure', 'user.session.lockout')
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 20;
EOF
```

### Check TOTP Setup/Disable Events

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- 2FA enable/disable audit trail
SELECT created_at, actor_id, action, details
FROM audits
WHERE action LIKE '%totp%'
ORDER BY created_at DESC
LIMIT 50;
EOF
```

### Check User Sessions

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Active sessions for a user
SELECT s.token, s.created_at, s.expires_at, u.email
FROM sessions s
JOIN users u ON s.user_id = u.id
WHERE u.email = 'admin@example.com'
ORDER BY s.created_at DESC;
EOF
```

---

## Emergency Procedures

### Admin is Locked Out of Account

#### Symptom
Admin receives "Could not authenticate with the provided credentials" repeatedly, even with correct password.

#### Cause
Likely 5 failed login attempts within 5 minutes from their IP address.

#### Resolution

**Option 1: Wait for automatic unlock** (10 minutes by default)
- The lockout automatically expires after the configured duration
- No action needed

**Option 2: Clear lockout by IP** (if needed immediately)

Currently, there is no built-in API endpoint to clear web-user login lockouts. Workaround:

```bash
# Option A: Database approach (requires DB access)
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
DELETE FROM audits
WHERE action = 'user.session.lockout'
  AND JSON_EXTRACT(details, '$.email') = 'admin@example.com'
  AND created_at > NOW() - INTERVAL '15 minutes';
EOF
```

**Note**: This removes the lockout audit records, allowing login to proceed. Adjust the time window as needed.

### Admin Lost Authenticator App

#### Scenario
Admin lost or broke their phone with the authenticator app installed and doesn't have backup codes saved.

#### Resolution

1. **Via backup codes (if saved)**:
   - Use one of the 12 backup codes instead of the 6-digit TOTP code
   - Each code works once

2. **Via backup codes (if not saved)**:
   - Another admin can temporarily disable 2FA (see below)
   - User re-enables with a new device

3. **Disable 2FA for the user**:
   ```bash
   docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
   DELETE FROM vg_user_totp WHERE user_id = (
     SELECT id FROM users WHERE email = 'admin@example.com'
   );
   EOF
   ```
   - User logs in without 2FA
   - User immediately re-enables 2FA on new device
   - User saves backup codes this time!

### Admin Lost Backup Codes

#### Scenario
Admin still has access to authenticator app but lost the backup codes.

#### Resolution

**Step 1: Log in with authenticator app**
- User can log in normally with their 6-digit TOTP code

**Step 2: Regenerate backup codes**
- Navigate to **Account Settings** → **Two-Factor Authentication**
- Click **Regenerate Backup Codes**
- Enter password when prompted
- Download and save the new codes

**If user can't access their account** (e.g., IP restricted):
- Admin can whitelist their IP via **Account Settings** → **IP Whitelist**
- Or temporarily disable 2FA (above) and have them re-enable

---

## Troubleshooting

### "Invalid code" error on login

**Possible causes:**
1. User entered wrong code - time-based codes change every 30 seconds
2. Device clock skew - user's phone/device time is out of sync
3. User's secret key was compromised - regenerate

**Resolution:**
- Have user try again with a fresh 6-digit code
- Check device clock is synchronized
- If repeated failures, have user regenerate backup codes

### User locked out after too many failed attempts

**Error**: "Could not authenticate with the provided credentials" even with correct password

**Resolution:**
- Wait 10 minutes for automatic unlock, OR
- Use the database procedure (see Emergency Procedures above)

### "TOTP required" on login but user already has 2FA enabled

**Cause**: Likely a race condition or cache issue

**Resolution:**
1. Have user try logging out and logging in again
2. Check `vg_user_totp` table to verify entry exists:
   ```bash
   docker exec -it central-postgres14-1 psql -U odk -d odk -c \
     "SELECT * FROM vg_user_totp WHERE user_id = (SELECT id FROM users WHERE email = 'admin@example.com');"
   ```

### Users can't log in after enabling mandatory 2FA

**Cause**: Not all users have 2FA enabled yet

**Solution**:
- Don't enable mandatory 2FA until all users have voluntarily set it up
- Provide clear communication and deadline for users to enable 2FA
- Consider a grace period during which 2FA is encouraged but not required

---

## Security Best Practices

### For Admins

1. **Backup codes**: Save in a secure location (password manager, encrypted vault)
   - NOT in the same place as your password
   - NOT in an email or cloud storage without encryption
   - NOT on a sticky note!

2. **Authenticator app**: Use a reputable app
   - Google Authenticator
   - Microsoft Authenticator
   - Authy (supports cloud backup)
   - Any app that supports TOTP standard

3. **Test before enforcing**: In production, test 2FA setup on your own account before making it mandatory

### For Deployments

1. **No single point of failure**: Have at least 2 admins with 2FA set up
2. **Emergency access**: Document your emergency procedures and test them quarterly
3. **Audit trail**: Regularly review audit logs for suspicious login patterns
4. **Rate limiting**: Configure appropriate lockout duration (not too long = usability, not too short = security)

---

## Related Documentation

- [VG: Two-Factor Authentication User Guide](vg_2fa_user_guide.md)
- [VG: IP Whitelist Admin Guide](vg_ip_whitelist_admin_guide.md)
- [VG: Implementation Details](vg_implementation.md)
- [Web User Login Hardening](web-user-lockout-implementation.md)

---

**Need help?** Check the troubleshooting section above, or file an issue in your project repository.
