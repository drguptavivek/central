# VG: IP Whitelist Admin Guide (API Access)

**Last Updated**: 2026-02-08
**Status**: ✅ Production Ready

---

## Overview

This guide covers administrative operations for IP Whitelist in ODK Central. IP whitelist restricts a web user's **API access** (dashboards, integrations, external applications) to specific IP addresses or CIDR ranges.

**Important Distinction**:
- **2FA** = protects web user login (admin dashboard access)
- **IP Whitelist** = protects API access (dashboards, external apps calling the Central API)
- **App Users** (Collect) are NOT affected by IP whitelist

---

## Table of Contents

1. [Understanding IP Whitelist](#understanding-ip-whitelist)
2. [How It Works](#how-it-works)
3. [User Management](#user-management)
4. [Monitoring & Auditing](#monitoring--auditing)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices](#best-practices)

---

## Understanding IP Whitelist

### What is IP Whitelist?

IP Whitelist restricts account access to specific IP addresses or networks:
- **Web login**: User can only log in from whitelisted IPs
- **API access**: App users can only authenticate from whitelisted IPs
- **Granular control**: Per-user configuration, not system-wide

### IP vs CIDR

- **IP Address**: Single machine (e.g., `192.168.1.100`)
- **CIDR Range**: Network of machines (e.g., `192.168.1.0/24` = 254 addresses)

### How It Complements 2FA

| Feature | 2FA | IP Whitelist |
|---------|-----|--------------|
| **What it protects** | Web user login access | API access from external apps/dashboards |
| **Where it applies** | Admin dashboard login | API calls (dashboards, integrations) |
| **User impact** | Need authenticator app to log in | API only works from whitelisted servers |
| **Best for** | All admin accounts | Sensitive API integrations, known servers |
| **Optional?** | Can be mandatory | Always optional (API key security first) |

**Recommendation**:
- **2FA**: Mandatory for all web admins
- **IP Whitelist**: Recommended for sensitive API operations (deletion endpoints, etc.)

---

## How It Works

### IP Whitelist Flow

```
User attempts login from 192.168.1.50
        ↓
Is IP in whitelist?
        ├─ YES → Continue to password/2FA
        └─ NO → Reject with "IP not whitelisted"
```

### Database Schema

```sql
-- View IP whitelist entries
SELECT id, actor_id, ip_cidr, description, enabled, created_at
FROM vg_user_ip_whitelist
ORDER BY created_at DESC;

-- Filter by user
SELECT * FROM vg_user_ip_whitelist
WHERE actor_id = (SELECT id FROM users WHERE email = 'user@example.com');
```

---

## User Management

### View User's IP Whitelist

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Get all whitelisted IPs for a user
SELECT w.id, w.ip_cidr, w.description, w.enabled, w.created_at,
       u.email as created_by
FROM vg_user_ip_whitelist w
JOIN users u ON w.created_by_id = u.id
WHERE w.actor_id = (
  SELECT id FROM users WHERE email = 'admin@example.com'
)
ORDER BY w.created_at DESC;
EOF
```

### Check All IP Whitelists in System

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Count of whitelisted IPs per user
SELECT u.email, COUNT(w.id) as ip_count,
       MIN(CASE WHEN w.enabled THEN 1 ELSE 0 END) as has_enabled
FROM users u
LEFT JOIN vg_user_ip_whitelist w ON u.id = w.actor_id
GROUP BY u.id, u.email
HAVING COUNT(w.id) > 0
ORDER BY ip_count DESC;
EOF
```

### Add IP Entry for a User (via API)

```bash
# Get auth token
TOKEN=$(curl -s -X POST https://central.local/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"PASSWORD"}' \
  | jq -r '.token')

# Add IP whitelist entry
curl -X POST https://central.local/v1/users/1/ip-whitelist \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "ipCidr": "192.168.1.0/24",
    "description": "Office network"
  }'
```

### Delete IP Entry for a User (Database)

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Find entry ID
SELECT id, ip_cidr FROM vg_user_ip_whitelist
WHERE actor_id = (SELECT id FROM users WHERE email = 'admin@example.com');

-- Delete entry (replace <id> with actual ID)
DELETE FROM vg_user_ip_whitelist WHERE id = <id>;

-- Verify deletion
SELECT * FROM vg_user_ip_whitelist
WHERE actor_id = (SELECT id FROM users WHERE email = 'admin@example.com');
EOF
```

### Disable/Enable IP Entry (without deletion)

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Disable all IP whitelist entries for a user
UPDATE vg_user_ip_whitelist
SET enabled = false
WHERE actor_id = (SELECT id FROM users WHERE email = 'admin@example.com');

-- Enable a specific IP entry
UPDATE vg_user_ip_whitelist
SET enabled = true
WHERE id = <entry_id>;
EOF
```

---

## Monitoring & Auditing

### Check IP Whitelist Violations

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Track IP rejections (audit trail)
SELECT created_at, action, details
FROM audits
WHERE action IN ('vg.ip_whitelist.violation', 'vg.ip_whitelist.denied')
ORDER BY created_at DESC
LIMIT 50;

-- Current format stores:
-- - email (user attempting login)
-- - ip (their IP address)
-- - expected_cidrs (whitelisted ranges)
EOF
```

### Monitor API Access by IP

For App User API access (Collect):

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Check app-user sessions by IP
SELECT s.token, s.created_at, s.expires_at,
       fk.display_name, fk.username, u.email as creator
FROM sessions s
JOIN field_keys fk ON s.actor_id = fk.id
JOIN users u ON fk.created_by = u.id
WHERE s.created_at > NOW() - INTERVAL '1 day'
ORDER BY s.created_at DESC;

-- Note: IP information is stored in vg_app_user_sessions table
SELECT * FROM vg_app_user_sessions
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
EOF
```

### Audit Trail of IP Whitelist Changes

```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
-- Track all IP whitelist modifications
SELECT created_at, actor_id, action, details
FROM audits
WHERE action LIKE 'vg.ip_whitelist%'
ORDER BY created_at DESC
LIMIT 100;

-- Expected actions:
-- vg.ip_whitelist.create
-- vg.ip_whitelist.update (enable/disable/modify IP/description)
-- vg.ip_whitelist.delete
EOF
```

---

## Troubleshooting

### User locked out - "IP not whitelisted"

**Symptom**: User can't log in, gets error "Your IP address is not whitelisted for this account"

**Diagnosis**:
1. Check user's whitelist entries:
   ```bash
   docker exec -it central-postgres14-1 psql -U odk -d odk -c \
     "SELECT ip_cidr, enabled FROM vg_user_ip_whitelist WHERE actor_id = (SELECT id FROM users WHERE email = 'user@example.com');"
   ```

2. Verify user's current IP matches whitelist:
   - Check your web server logs or firewall logs for user's IP
   - Compare against `ip_cidr` values

**Resolution**:

**Option A**: Disable whitelist temporarily
```bash
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
UPDATE vg_user_ip_whitelist
SET enabled = false
WHERE actor_id = (SELECT id FROM users WHERE email = 'admin@example.com');
EOF
```

**Option B**: Add current IP to whitelist
```bash
# Identify user's public IP (e.g., 203.0.113.45)
# Then add to whitelist:
docker exec -it central-postgres14-1 psql -U odk -d odk << 'EOF'
INSERT INTO vg_user_ip_whitelist (actor_id, ip_cidr, description, enabled, created_by_id, created_at)
VALUES (
  (SELECT id FROM users WHERE email = 'admin@example.com'),
  '203.0.113.45',  -- User's IP
  'Added for emergency access',
  true,
  1,  -- Admin user ID
  NOW()
);
EOF
```

### "Invalid CIDR notation" error

**Cause**: User entered invalid CIDR format

**Valid formats**:
- Single IP: `192.168.1.100` or `192.168.1.100/32`
- CIDR range: `192.168.0.0/16` or `192.168.1.0/24`
- IPv6: `2001:db8::/32` or `2001:db8::1/128`

**Invalid formats** (will be rejected):
- `192.168.1` (incomplete)
- `192.168.1.0/33` (prefix too large)
- `192.168.1.0/16` (wrong prefix for network)
- `256.0.0.1` (octet out of range)

### Dynamic IP ranges changing frequently

**Problem**: User has a dynamic/changing IP address

**Solution 1**: Use wider CIDR range
- If ISP uses `203.0.113.0 - 203.0.113.255`
- Add `203.0.113.0/24` instead of individual IPs
- Client can warn: "You're whitelisting many IP addresses"

**Solution 2**: Use VPN/Fixed IP
- User connects through VPN with static IP
- Or use corporate proxy with fixed exit IP
- Then whitelist just that IP

**Solution 3**: Disable whitelist
- If too restrictive for user's use case
- Fall back to just 2FA for security

---

## Best Practices

### For Admins

1. **Use CIDR notation for ranges**
   - ✅ Good: `192.168.0.0/16` (whole subnet)
   - ❌ Bad: `192.168.1.1`, `192.168.1.2`, `192.168.1.3` (individual IPs)

2. **Warn against too-wide ranges**
   - ⚠️ `/16` covers 65,536 addresses
   - ⚠️ `/8` covers 16 million addresses
   - ⚠️ `/0` disables whitelist completely

3. **Document purpose**: Always add descriptions
   - ✅ Good: "Office network, ISP: XYZ, 9am-5pm PT"
   - ❌ Bad: (empty)

4. **Test before deploying**: In production, have users test from expected IPs first
   - Add whitelist entry
   - Have user log in and verify
   - User confirms success before finalizing

5. **Maintain audit trail**: Review IP whitelist changes monthly

### For Users

1. **Only whitelist trusted networks**:
   - ✅ Office network
   - ✅ Home network (if using static IP)
   - ❌ Public WiFi
   - ❌ Unknown/shared networks

2. **Don't whitelist `/0` (all IPs)**:
   - Defeats the purpose of IP whitelist
   - Equivalent to disabling the feature
   - Use only if combined with 2FA and strong passwords

3. **Test access before saving**:
   - Add whitelist entry
   - Try logging in from that IP
   - Confirm success
   - Verify you're not locked out

4. **Plan for travel**:
   - Need to access from multiple locations?
   - Add each location's IP or CIDR range
   - Or use VPN to single trusted endpoint

---

## Integration with 2FA

### Recommended Security Posture

| User Type | 2FA | IP Whitelist | Notes |
|-----------|-----|--------------|-------|
| **Admin** | ✅ Required | ✅ Recommended | Most restrictive |
| **API User (Collect)** | ✅ (App) | ✅ Recommended | Via bearer token + IP |
| **Power User** | ✅ Required | ⚠️ Optional | If office-based |
| **Data Viewer** | ⚠️ Optional | ⚠️ Optional | Lower privilege |

### Defense in Depth

```
Login Attempt
    ↓
[2FA Check] ← Password correct?
    ↓ (TOTP/backup code valid)
[IP Whitelist Check] ← IP in whitelist?
    ↓ (enabled)
[Rate Limiting Check] ← Not locked out?
    ↓
Login Success
```

---

## Related Documentation

- [VG: Two-Factor Authentication Admin Guide](vg_2fa_admin_guide.md)
- [VG: IP Whitelist User Guide](vg_ip_whitelist_user_guide.md)
- [VG: Implementation Details](vg_implementation.md)
- [Web User Login Hardening](web-user-lockout-implementation.md)

---

**Need help?** Check the troubleshooting section above, or file an issue in your project repository.
