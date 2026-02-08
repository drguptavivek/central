# VG: Two-Factor Authentication (2FA) User Guide

**Last Updated**: 2026-02-08
**Status**: ✅ Ready for Users

---

## What is Two-Factor Authentication?

Two-Factor Authentication (2FA) is an extra layer of security for your account. Even if someone gets your password, they still can't log in without your authenticator app.

### How it works:
1. You enter your **email and password** (first factor)
2. You enter a **6-digit code from your authenticator app** (second factor)
3. Only then can you access your account

This makes your account much more secure! 🔒

---

## Table of Contents

1. [Setting Up 2FA](#setting-up-2fa)
2. [Logging In With 2FA](#logging-in-with-2fa)
3. [Using Backup Codes](#using-backup-codes)
4. [Managing Your 2FA](#managing-your-2fa)
5. [Troubleshooting](#troubleshooting)
6. [Frequently Asked Questions](#frequently-asked-questions)

---

## Setting Up 2FA

### Step 1: Start the Setup Wizard

1. Log in to ODK Central
2. Click on your **profile menu** (top right corner)
3. Select **Account Settings**
4. Scroll down to **Two-Factor Authentication (2FA)**
5. Click **Enable 2FA**

### Step 2: Scan the QR Code

You should see a screen with:
- A **QR code** on the left
- A **secret key** (if you need to type it manually)
- Instructions

**Choose an authenticator app:**
- ✅ Google Authenticator (iPhone/Android)
- ✅ Microsoft Authenticator (iPhone/Android)
- ✅ Authy (iPhone/Android/Chrome)
- ✅ 1Password (iPhone/Android)
- ✅ Any app supporting TOTP standard

**To scan the QR code:**
1. Open your authenticator app
2. Tap "+" to add a new account
3. Choose "Scan QR code"
4. Point your phone camera at the QR code on screen
5. The app should recognize it and add "ODK Central"

**Can't scan?**
- Try "Enter manually" in your app
- Copy-paste the secret key shown on screen
- The key format looks like: `JBSWY3DPEBLW64TMMQ======`

### Step 3: Verify Your Code

Once your authenticator app shows a 6-digit code:
1. Enter that code in the text field
2. Click **Next**

**Important**: These codes change every 30 seconds, so enter it quickly!

### Step 4: Save Your Backup Codes

A new screen shows **12 backup codes**. These are VERY IMPORTANT:

**What are they for?**
- If you lose your phone/authenticator app
- If your authenticator app gets deleted
- If you want to log in from a new device immediately

**How to save them:**
- ✅ Download as a `.txt` file and store securely
- ✅ Copy and paste into a password manager
- ✅ Write them down and store in a safe place
- ❌ DON'T email them to yourself
- ❌ DON'T store on your phone where you also have the authenticator app
- ❌ DON'T share with anyone

**One-time use**: Each backup code can only be used ONCE. Once used, it's gone. So you have 12 tries if you lose your authenticator.

### Step 5: Confirm Setup

Check the box **"I have saved my backup codes in a secure location"** and click **Enable 2FA**.

✅ **Done!** Your account is now protected with 2FA!

---

## Logging In With 2FA

### Normal Login (with authenticator)

1. Enter your **email** and **password**
2. Click **Log In**
3. You'll see a new screen: **"Enter 6-digit code"**
4. Open your authenticator app
5. Find the code for "ODK Central"
6. Enter the 6-digit code
7. Click **Verify**

**Codes change every 30 seconds!** If it seems to be taking too long, try getting a fresh code.

### Backup Code Login

**When to use backup codes:**
- You lost your authenticator app
- Your phone doesn't have the app anymore
- You're setting up a new phone and need immediate access

**How to use a backup code:**

1. On the **"Enter 6-digit code"** screen
2. Check the box **"Use backup code instead"**
3. The field will change to accept a longer code
4. Enter one of your 12 backup codes (12 digits, like: `123456789012`)
5. Click **Verify**

⚠️ **After using a backup code**: It's gone forever! You now have 11 codes left.

---

## Using Backup Codes

### Saving Your Backup Codes (Critical!)

After setup, you'll see 12 codes:
```
1. 234567890123
2. 345678901234
3. 456789012345
... (9 more)
```

**Choose ONE of these storage options:**

#### Option 1: Download as File (Easiest)
- Click **Download Codes** button
- File `odk-central-backup-codes.txt` downloads
- Move to a secure location (encrypted storage, password manager)

#### Option 2: Copy to Password Manager
- Click **Copy to Clipboard** button
- Open your password manager (1Password, LastPass, Bitwarden, etc.)
- Create a new entry for "ODK Central Backup Codes"
- Paste the codes
- Save

#### Option 3: Write Down
- Get a pen and paper
- Copy down all 12 codes
- Store in a safe place (home safe, safety deposit box)

#### Option 4: Multiple Locations
- Best practice: Store in 2+ locations
- E.g., password manager + printed copy

### Using a Backup Code

See **Backup Code Login** section above.

### Regenerating Backup Codes

After using some codes, you can generate a fresh set of 12:

1. Log into your account
2. Go to **Account Settings** → **Two-Factor Authentication**
3. Click **Regenerate Backup Codes**
4. Enter your password to confirm
5. Save the new codes
6. Old codes are now **useless** (even if not used yet!)

⚠️ **Important**: When you regenerate, all OLD codes become invalid. Keep only the newest ones!

---

## Managing Your 2FA

### View Your 2FA Status

1. Log in to your account
2. Click your **profile menu** (top right)
3. Select **Account Settings**
4. Scroll to **Two-Factor Authentication (2FA)**

You'll see:
- ✅ **Status**: "Two-factor authentication is enabled" OR ❌ "is not enabled"
- 📅 **Date enabled**: When you set it up
- 🔄 **Buttons**: Regenerate Backup Codes, Disable 2FA

### Regenerate Backup Codes (New Set)

If you used some backup codes and want a fresh set of 12:

1. Go to **Account Settings** → **Two-Factor Authentication**
2. Click **Regenerate Backup Codes**
3. Enter your password
4. **Save the new codes** (old ones won't work anymore!)

### Disable 2FA (Remove Protection)

⚠️ **Warning**: Disabling 2FA makes your account less secure!

To disable:
1. Go to **Account Settings** → **Two-Factor Authentication**
2. Click **Disable 2FA**
3. Enter your password to confirm
4. 2FA is now OFF (next login won't ask for a code)

---

## Troubleshooting

### "Invalid code" error

**Problem**: You entered a code but got an error.

**Common causes & solutions:**

| Cause | Solution |
|-------|----------|
| Entered wrong code | Try the next code (they change every 30 seconds) |
| Phone time is wrong | Go to phone Settings → Date & Time → set "Automatic" |
| App wasn't set up correctly | Delete and re-add the account in your authenticator app |
| Code expired | Codes only last ~30 seconds - get a fresh one |

**Still not working?**
- Open your authenticator app
- Make sure it shows "ODK Central"
- Make sure the number is changing every 30 seconds
- If not, re-add the account to your app

### Lost Your Authenticator App

**Scenario**: Your phone broke, got stolen, or the app was deleted.

**Solution**: Use a backup code!

1. On the login screen, you'll see **"Use backup code instead"** option
2. Check that box
3. Enter one of your backup codes (12 digits)
4. Once logged in, you can get new backup codes OR set up 2FA on a new device

**If you also lost your backup codes**:
- Contact your ODK Central administrator
- They can help reset your 2FA (you may need to prove your identity)

### Locked Out of Account

**Scenario**: You've tried logging in too many times and got an error.

**Why**: After 5 failed login attempts in 5 minutes, your account is temporarily locked.

**Solution**: Wait 10 minutes and try again.

If you keep getting errors after 10 minutes:
- Contact your administrator
- They can temporarily disable 2FA to help you regain access

### Authenticator App Not Generating Codes

**Check:**
1. Do you see "ODK Central" in your app? If not, re-add it.
2. Is the code number changing every 30 seconds? If not, your phone clock might be wrong.
3. Did you use the correct secret key when setting up? If unsure, disable 2FA and set up again.

---

## Frequently Asked Questions

### Q: Do I need to buy special hardware?
**A**: No! Any smartphone with an authenticator app works. Google Authenticator is free and available on iOS and Android.

### Q: What if my phone doesn't have cell service?
**A**: No problem! Authenticator apps work offline. You don't need internet to generate the codes.

### Q: Can multiple people have the same authenticator app?
**A**: Yes, but it's NOT recommended for security. Each person should have their own device and account.

### Q: What if I get a new phone?
**A**:
1. Install your authenticator app on the new phone
2. Use one of your backup codes to log in to ODK Central
3. Go to Account Settings and disable 2FA
4. Set up 2FA again with your new phone
5. Save the new backup codes

### Q: What happens if someone steals my backup codes?
**A**: They could log into your account (if they also have your password). To prevent this:
- Store backup codes somewhere safe (not in your phone)
- If codes are compromised, regenerate a new set immediately
- Use strong passwords + 2FA + IP whitelist together for best security

### Q: Can I use the same backup code twice?
**A**: No. Each code works only once. Once used, it's gone.

### Q: What if my authenticator app crashes and loses all codes?
**A**:
1. Use one of your backup codes to log in
2. Delete the authenticator app and reinstall it
3. Re-add your ODK Central account using the secret key shown in Account Settings
4. Generate new backup codes

### Q: Is 2FA required or optional?
**A**: Depends on your administrator's settings:
- ⚠️ **Required**: You must enable 2FA to use your account (you'll be prompted)
- ✅ **Optional**: You can choose to enable it for extra security

Ask your administrator if you're unsure.

### Q: Can I use SMS (text message) codes instead?
**A**: Not currently. ODK Central uses authenticator apps (Google Authenticator, Authy, etc.) which are more secure than SMS.

### Q: Do backup codes work forever?
**A**: No. When you regenerate a new set of backup codes, the old ones stop working (even if unused).

### Q: What's the difference between TOTP and backup codes?
| Feature | TOTP (Authenticator) | Backup Code |
|---------|---------------------|----|
| **Type** | Time-based, changes every 30s | Static, 12-digit codes |
| **When to use** | Normal logins | If you lose your authenticator app |
| **Renewable** | No (same secret) | Yes (can regenerate new set) |
| **Reusable** | Yes (code changes) | No (one-time use per code) |

---

## Related Guides

- [Account Settings Overview](../README.md)
- [IP Whitelist Guide](vg_ip_whitelist_user_guide.md) - Restrict login to specific networks
- [Password Management](../README.md)

---

**Still have questions?** Contact your ODK Central administrator or check the FAQ above!

**Security reminder**: Enable 2FA today to protect your account! 🔒
