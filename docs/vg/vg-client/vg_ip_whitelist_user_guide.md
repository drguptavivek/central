# VG: IP Whitelist User Guide (API & Integrations)

**Last Updated**: 2026-02-08
**Status**: ✅ Ready for Users

---

## What is IP Whitelist?

IP Whitelist restricts API access to your account so it can ONLY be used from specific IP addresses or networks that you approve. This is for protecting your **API credentials** when you use Central as an API endpoint (dashboards, integrations, custom apps, etc.).

**Important**: This is for API access only - not for web login. Your web login is protected by your password and 2FA.

### Example:
- ✅ Your dashboard server at `10.0.1.50` can access the API (whitelisted)
- ❌ Someone with your API credentials can't use them from `192.0.2.0` (not whitelisted)
- ✅ Your integration server at `10.0.2.100` can access the API IF you added it (whitelisted)

This is an optional extra layer of security for API users! 🔒

---

## Table of Contents

1. [When to Use IP Whitelist](#when-to-use-ip-whitelist)
2. [How IP Whitelist Works](#how-ip-whitelist-works)
3. [Setting Up IP Whitelist](#setting-up-ip-whitelist)
4. [Managing Entries](#managing-entries)
5. [Testing & Troubleshooting](#testing--troubleshooting)
6. [Frequently Asked Questions](#frequently-asked-questions)

---

## When to Use IP Whitelist

### Perfect for IP Whitelist:

✅ **Dashboards accessing Central API**
- PowerBI dashboard connecting to Central
- Tableau integration with fixed server IP
- Custom web dashboard pulling data from Central

✅ **Data integration jobs**
- Nightly ETL jobs running from specific server
- Data warehouse sync from fixed IP
- Custom integrations with known server address

✅ **Mobile dashboards in offices**
- Mobile analytics app running on office network
- Fixed IP range for office building

✅ **API keys with sensitive access**
- Keys that can delete data
- Keys with high usage rates
- Keys exposed in client-side code

✅ **Combined with strong authentication**
- IP whitelist + strong API key = very strong security
- Even if API key is compromised, it won't work from other IPs

### Not ideal for IP Whitelist:

❌ **Dynamic server IPs**
- Cloud services with rotating IPs
- Serverless functions with changing IPs
- Third-party APIs with variable IPs

❌ **Accessing from multiple locations**
- Need access from office + home + backup site
- Every location needs its own IP entry

❌ **Simple read-only access**
- Low-sensitivity data
- One-time reports
- Just use a read-only API key

---

## How IP Whitelist Works

### The API Request Flow

When your dashboard or integration tries to access the Central API:

```
Your dashboard/app makes API request
              ↓
    [Is the source IP whitelisted?]
          ↙          ↖
       YES            NO
        ↓              ↓
   API Success   API Denied
                "IP not whitelisted"
```

### Important Concepts

**IP Address**: Your server's address on the internet
- Example: `203.0.113.45`
- Like your server's home address on the internet
- Different servers have different IPs

**CIDR Range**: A range of IP addresses (a network)
- Example: `203.0.113.0/24` = 256 addresses
- Like saying "any server in this network"
- More flexible than listing single IPs

**Enabled vs Disabled**: Control without deletion
- ✅ **Enabled**: IP can access API, others cannot
- ⏸️ **Disabled**: Temporarily turned off, can re-enable later

### Example: Dashboard Server

Your PowerBI dashboard might be:
- **Server**: `10.0.1.50` (dashboard server IP)
- **API requests come from**: `10.0.1.50`
- **Whitelist entry**: `10.0.1.50/32` (only that server) OR `10.0.1.0/24` (dashboard subnet)

---

## Setting Up IP Whitelist

### Step 1: Find Your Server's IP Address

Before whitelisting, you need to know your server's public IP address.

**Find your server IP:**

**Method A: Identify from your infrastructure**
- Cloud provider (AWS, Azure, GCP, etc.) - shows instance public IP
- On-premises server - check your network admin
- Docker container - get host public IP

**Method B: Run a command on your server**
```bash
# From your dashboard/integration server
curl https://api.ipify.org
# Returns your public IP
```

**Method C: Check your dashboard logs**
- Check what IP Central sees when dashboard connects
- Found in Central's application logs

**Method D: Ask your IT team**
- Network team knows your server's public IP
- They might give you a CIDR range like `203.0.113.0/24`

### Step 2: Access IP Whitelist Settings

1. Log into ODK Central
2. Click your **profile menu** (top right)
3. Select **Account Settings**
4. Scroll to **IP Whitelist**

### Step 3: Add Your Server IP

Click **Add IP or CIDR Range**

**Enter:**
- **IP Address or CIDR Range** *:
  - Single server: `203.0.113.45` or `203.0.113.45/32`
  - Server subnet: `203.0.113.0/24`
  - IPv6: `2001:db8::1` or `2001:db8::/32`

- **Description**: (recommended for tracking!)
  - `PowerBI dashboard server`
  - `ETL job - nightly sync`
  - `Office analytics - fixed IP`
  - `Data warehouse integration`

Click **Add Entry**

✅ Done! Your server IP is now whitelisted.

### Step 4: Test API Access Works

**Test that your API can now connect:**

```bash
# From your dashboard/integration server
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  https://central.example.com/v1/projects

# Should return project list (not "IP not whitelisted" error)
```

✅ If you see project data, your whitelist is working!

---

## Managing Entries

### View Your Whitelisted IPs

In **Account Settings** → **IP Whitelist**, you'll see:
- 📍 Each IP/CIDR range you added
- 📝 Description you provided
- 👤 Who added it and when
- 🔘 Enable/Disable toggle
- 🗑️ Delete button

### Add More Locations

Need to work from multiple locations?

1. Click **Add IP or CIDR Range**
2. Enter the new location's IP
3. Add a description (e.g., "Mobile office, Tuesday-Thursday")
4. Click **Add Entry**

Now you can log in from both locations!

### Temporarily Disable (Pause) a Location

If you're traveling but want to keep your whitelist:

1. Find the IP entry
2. Click the **Disable** button
3. That IP is now temporarily off

**When you get back**, click **Enable** to turn it back on.

### Delete an Entry

Click the **Delete** button to remove an IP permanently.

⚠️ **Warning**: Once deleted, you can't use that IP anymore. Make sure you have other whitelisted IPs available!

### Edit an Entry (Update)

Want to change the description or IP?

1. Click the entry
2. Update the **Description** or **IP**
3. Click **Save**

---

## Testing & Troubleshooting

### Before Enabling Whitelist: Test!

**Critical**: Test your setup before relying on it!

1. **Add your server IP** to the whitelist
2. **Test API call**: Make an API request from your server
3. **Verify success**: Did you get data (not an error)? ✅
4. If yes, you're ready to rely on the whitelist
5. If no, see troubleshooting below

### "IP not whitelisted" Error in API Response

**You see**: API returns `401.2 "IP not whitelisted for this account"`

**Causes & solutions**:

| Cause | Solution |
|-------|----------|
| Server IP is wrong | Check actual IP (use `curl https://api.ipify.org`) |
| Server IP changed | Cloud/ISP assigned new IP; update whitelist |
| Forgot to add this server | Add the new server IP to your whitelist |
| Whitelist is too restrictive | Widen the CIDR range (use `/24` instead of `/32`) |
| Accidentally deleted entry | Re-add the IP or temporarily disable whitelist |
| Behind a proxy/NAT | The IP Central sees might be the proxy's IP, not your server's |

**Debugging:**
```bash
# Check what IP Central sees
# Enable verbose logging in your dashboard/app to see error details
# The error response should include which IP was rejected

# From Central's logs (admin only):
docker logs central-service | grep "ip_whitelist"
```

### Wrong CIDR Format

**Error**: "Invalid CIDR notation"

**Valid formats**:
- Single IP: `192.168.1.100` ✅
- Single IP explicit: `192.168.1.100/32` ✅
- Small range: `192.168.1.0/24` (256 IPs) ✅
- Larger range: `192.168.0.0/16` (65,536 IPs) ✅
- IPv6: `2001:db8::/32` ✅

**Invalid formats**:
- `192.168.1` ❌ (incomplete)
- `192.168.1.0/33` ❌ (prefix too large)
- `256.1.1.1` ❌ (octet out of range)

**Warning**: The system will warn you about:
- **Very wide ranges** (`/8` = 16 million IPs) - be careful!
- **Allows all IPs** (`/0`) - defeats the purpose!

### Dynamic IP (Keeps Changing)

**Problem**: Your IP keeps changing (home internet, mobile, etc.)

**Solutions**:

**Option 1: Use a wider CIDR range**
- Ask your ISP: "What IP range do you use?"
- They might use `203.0.113.0/24`
- Whitelist that range instead of single IP
- Downside: Less secure (anyone in that range can access)

**Option 2: Use a VPN**
- Get a VPN service (ProtonVPN, ExpressVPN, etc.)
- VPN will have a static IP (doesn't change)
- Whitelist your VPN's exit IP
- When traveling, connect to VPN, then access ODK Central

**Option 3: Disable whitelist**
- If too restrictive, just use password + 2FA
- Whitelist is optional

**Option 4: Whitelist multiple IPs**
- Add each location you use frequently
- E.g., home + office + mobile office + mom's house

### Testing API Access

If you're using **Collect** or **API client**:

1. **Get your current IP**: Run `curl https://api.ipify.org`
2. **Add to whitelist**: Use the account settings UI
3. **Test API call**:
   ```bash
   curl -H "Authorization: Bearer <YOUR_TOKEN>" \
     https://central.example.com/v1/projects
   ```
4. **Check response**:
   - ✅ If you get project data, it worked!
   - ❌ If you get "IP not whitelisted", check your IP

---

## Frequently Asked Questions

### Q: Do I need IP whitelist if my API key is strong?
**A**: No, a strong API key is sufficient. IP whitelist is optional extra protection for sensitive integrations.

### Q: Can I whitelist multiple server IPs for the same account?
**A**: Yes! Add as many servers as you need (dashboard, ETL job, backup, etc.). Each can be added separately.

### Q: What if my servers are behind a load balancer/NAT?
**A**: Ask your IT team:
- What's the exit IP of the load balancer/proxy?
- Whitelist that IP (it's what Central sees)

### Q: Will whitelist slow down my API calls?
**A**: No. It's instant and happens behind the scenes.

### Q: Can my colleagues see my whitelisted IPs?
**A**: No. Your whitelist is private - only you and admins can see it.

### Q: What's the difference between `/32` and `/24`?
| CIDR | Addresses | Use Case |
|------|-----------|----------|
| `/32` | 1 address | Single server (most secure) |
| `/24` | 256 addresses | Subnet/small network |
| `/16` | 65,536 addresses | Larger network |
| `/8` | 16 million addresses | ⚠️ Very wide, be careful |

Smaller number = larger range = less secure but more flexible.

### Q: What if I add `/0` (all IPs)?
**A**: It disables IP whitelist completely. Anyone with your API key can use it from anywhere. Not recommended!

### Q: Can I disable IP whitelist temporarily?
**A**: Yes! Click the **Disable** button next to the entry to pause it. Click **Enable** to turn it back on. Useful for maintenance/debugging.

### Q: How do I delete my entire whitelist?
**A**: Delete each entry one by one. Once all entries are deleted, the whitelist is inactive.

### Q: What if my server's IP changed?
**A**:
1. Identify the new IP
2. Update the whitelist entry with the new IP
3. Test that your API call works

### Q: Can I use IPv6?
**A**: Yes! Format like `2001:db8::/32` or `2001:db8::1`

### Q: Is IP whitelist checked for API only?
**A**: Yes, it applies only to API access:
- ✅ API calls (dashboards, integrations, custom apps)
- ✅ API token usage
- ❌ Does NOT affect web login (dashboard access use 2FA)

---

## Best Practices

### 1. Add Descriptions
✅ Good: "PowerBI dashboard - primary reporting"
❌ Bad: (empty)

**Why**: Helps track which servers/integrations need which IPs and audit changes.

### 2. Test Before Production
✅ Test your API connection before enabling whitelist.
✅ Start with disabled, enable once tested.
❌ Don't enable whitelist before verifying API works.

### 3. Keep a Fallback IP
✅ Add at least 2 server IPs (primary + backup)
✅ Add a development/test IP for debugging
❌ Don't whitelist only one IP - if that server fails, you have no access

### 4. Use CIDR for Server Subnets
✅ Use `203.0.113.0/24` for a cluster of servers
✅ Use `10.0.1.50/32` for a single server
❌ Don't add individual IPs if they're all in the same subnet

### 5. Combine With Strong API Key
✅ Use IP whitelist + read-only API keys (for read-only dashboards)
✅ Use IP whitelist + short-lived tokens (for temporary integrations)
❌ Don't rely on whitelist alone for sensitive operations

### 6. Review & Audit Regularly
✅ Monthly: Review your whitelist entries
✅ Remove servers that are no longer used
✅ Check audit logs for access attempts
❌ Don't leave old IPs pointing to decommissioned servers

---

## Security Considerations

### IP Whitelist Protects Against:
- Stolen/leaked API keys used from unauthorized locations
- Compromised API credentials used by attackers on other networks
- Unauthorized access even if API key is exposed
- Brute force attempts from external networks

### IP Whitelist Does NOT Protect Against:
- Weak API keys (use strong, random keys)
- Someone on an approved IP using your credentials
- Compromise of the server itself (fix the server, not the whitelist)
- Man-in-the-middle attacks (use HTTPS always - never HTTP)

### Best Security Posture for API:
1. ✅ Use strong, randomly generated API keys
2. ✅ Use read-only API keys for read-only access
3. ✅ IP whitelist for sensitive operations (optional, for extra defense)
4. ✅ Monitor API usage and audit logs
5. ✅ Rotate API keys regularly

---

## API Security: IP Whitelist vs. Strong Keys

| Feature | Strong API Key | IP Whitelist |
|---------|---|---|
| **What it does** | Prevents unauthorized API usage with random token | Restricts access to known server locations |
| **Protects against** | Credential guessing, brute force | Stolen credentials used from wrong location |
| **Best for** | All API access | Sensitive operations, known integrations |
| **How to use** | Generate strong keys, rotate regularly | Whitelist your servers' IPs |

**Recommendation**: Use both for maximum security on sensitive operations!

---

## Related Guides

- [Two-Factor Authentication (2FA) Guide](vg_2fa_user_guide.md) - For web user login security
- [Account Settings Overview](../README.md)
- [API Key Management](../README.md)

---

**Questions?** Ask your ODK Central administrator or contact your IT team!

**🔒 Security reminder**: Use strong API keys + IP whitelist for maximum API security!
