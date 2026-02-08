# TOTP 2FA Client Implementation Guide

**Last Updated:** 2026-02-08
**Status:** ✅ Production Ready

---

## Overview

Client-side implementation of Two-Factor Authentication (2FA) using Time-based One-Time Passwords (TOTP). This guide covers:
- Two-phase login flow
- TOTP setup process
- TOTP verification
- Session state management
- Error handling

---

## Component Architecture

### Login Flow Components

```
AccountLogin
├── Phase 1: Email/Password form
├── Phase 2: TOTP code entry (conditional)
└── VgTotpSetupModal (when enabling 2FA)

UserEditVgTotpSettings
├── Display current 2FA status
├── Enable/Disable 2FA
└── Regenerate backup codes
```

### Files

**Location:** `/client/src/components/account/`
- `login.vue` - Two-phase login implementation
- `user/edit/vg-totp-settings.vue` - User 2FA settings panel

**Location:** `/client/src/components/vg/`
- `vg-totp-setup-modal.vue` - Multi-step TOTP setup wizard

**Location:** `/client/src/util/`
- `session.js` - Session management and TOTP verification checks

---

## Phase 1: Password Login

### Code: `login.vue` - Lines 220-256

```vue
<script>
submit() {
  if (!this.requiresTotp) {
    // Phase 1: Submit email and password
    this.session.request({
      method: 'POST',
      url: '/v1/sessions',
      data: { email: this.email, password: this.password },
      alert: false
    })
      .then((response) => {
        // Check if TOTP is required
        if (response.data && response.data.requireTotp) {
          this.requiresTotp = true;  // ← Show TOTP input
          this.disabled = false;
        } else {
          // No TOTP required, proceed with login
          return logIn(this.container, true)
            .then(() => this.navigateToNext(...));
        }
      })
      .catch((error) => {
        this.disabled = false;
        const message = requestAlertMessage(this.$i18n, error);
        this.alert.danger(message);
      });
  }
}
</script>
```

### Response Handling

```javascript
Response: {
  token: "...",
  totp_verified: false,
  requireTotp: true  // ← Critical flag
}

if (response.data.requireTotp) {
  // Show TOTP entry screen
  this.requiresTotp = true;
}
```

---

## Phase 2: TOTP Verification

### Code: `login.vue` - Lines 276-308

```vue
<script>
submit() {
  if (this.requiresTotp) {
    // Phase 2: Submit TOTP code
    const data = {
      token: this.totpCode  // 6-digit code from authenticator
    };

    this.session.request({
      method: 'POST',
      url: '/v1/sessions/totp-verify',
      data,
      alert: false
    })
      .then(() => {
        // TOTP verified successfully
        return logIn(this.container, true);
      })
      .then(() => {
        // Session is now fully authenticated
        this.navigateToNext(...);
      })
      .catch((error) => {
        this.disabled = false;
        const message = requestAlertMessage(
          this.$i18n,
          error,
          (problem) => {
            if (problem.code === 401.7) {
              return this.$t('problem.invalidTotpCode');
            }
            return null;
          }
        );
        this.alert.danger(message);
      });
  }
}
</script>
```

### Key Points

1. **Only send the 6-digit code** (not the temporary session token)
2. **Session.request() handles authentication** automatically with the session cookie
3. **Wait for success before navigating** to app
4. **On error 401.7** show "Invalid code" message
5. **Clear and retry** if user enters wrong code

---

## Session Restoration (Page Reload Protection)

### Code: `util/session.js` - Lines 275-312

```javascript
export const restoreSession = (session) =>
  session.request({ url: '/v1/sessions/restore', alert: false })
    .then((response) => {
      // VG: Check if TOTP verification is required but not yet completed
      if (response && response.data && response.data.totp_verified === false) {
        // Session exists but TOTP is not verified - user must not proceed
        session.data = null;  // ← Clear session state
        removeSessionFromStorage();
        throw new Error('TOTP verification required');
      }
    })
    .catch(error => {
      if (error.message === 'TOTP verification required') {
        // Expected: User must complete TOTP
        removeSessionFromStorage();
        return;  // Don't throw, just clear session
      }

      // Handle other errors (401, etc.)
      const { response } = error;
      if (response != null && isProblem(response.data) &&
        (response.data.code === 401.2 || response.data.code === 401)) {
        removeSessionFromStorage();
        return;
      }

      throw error;
    });
```

### Protection Mechanism

```
Page reload detected
    ↓
GET /v1/sessions/restore called
    ↓
Response arrives: { totp_verified: false }
    ↓
Frontend action:
  - Set session.data = null
  - Remove sessionExpires from localStorage
    ↓
Session is considered "logged out"
    ↓
User must complete TOTP verification
```

### Why This Works

- `session.data = null` signals to Vue reactivity that session is empty
- Frontend components check `session.dataExists` before rendering app
- Redirect to login/TOTP happens automatically
- Cookie still exists but is useless without valid session state

---

## TOTP Setup Modal: `vg-totp-setup-modal.vue`

### Four-Step Wizard

#### Step 1: Scan QR Code
```vue
<template v-if="step === 1">
  <img :src="qrCodeDataUrl" alt="QR code">
  <div class="secret-key">{{ secret }}</div>
  <p>Scan with Google Authenticator, Microsoft Authenticator, Authy, etc.</p>
</template>
```

#### Step 2: Verify Code
```vue
<template v-else-if="step === 2">
  <input v-model="verificationCode"
         type="text"
         inputmode="numeric"
         maxlength="6"
         pattern="[0-9]{6}">
  <button @click="verifyCode">Next</button>
</template>

// Code: Lines 224-240
verifyCode() {
  this.request({
    method: 'POST',
    url: '/v1/users/:id/totp/enable',
    data: { token: this.verificationCode }  // ← 6-digit code
  })
    .then(() => {
      this.step = 3;  // Show backup codes
    })
    .catch(({ problem }) => {
      if (problem.code === 401.7) {
        this.verificationError = 'Invalid code';
      }
    });
}
```

#### Step 3: Save Backup Codes
```vue
<template v-else-if="step === 3">
  <table class="backup-codes-table">
    <tr v-for="idx in 5">
      <td>{{ backupCodes[idx - 1] }}</td>
      <td>{{ backupCodes[idx + 4] }}</td>
    </tr>
  </table>
  <button @click="downloadBackupCodes">Download</button>
  <button @click="copyBackupCodes">Copy</button>
</template>

// Code: Lines 248-269
downloadBackupCodes() {
  const text = this.backupCodes.join('\n');
  const element = document.createElement('a');
  element.setAttribute('href', `data:text/plain;charset=utf-8,${encodeURIComponent(text)}`);
  element.setAttribute('download', 'odk-central-backup-codes.txt');
  element.click();
}

copyBackupCodes() {
  const text = this.backupCodes.join('\n');
  navigator.clipboard.writeText(text)
    .then(() => {
      this.copySuccess = true;
      setTimeout(() => { this.copySuccess = false; }, 3000);
    });
}
```

#### Step 4: Confirmation
```vue
<template v-else-if="step === 4">
  <input v-model="codesConfirmed" type="checkbox">
  <label>I have saved my backup codes</label>
  <button @click="completeSetup"
          :disabled="!codesConfirmed">
    Enable 2FA
  </button>
</template>

// Code: Lines 242-246
completeSetup() {
  this.$emit('success');
  this.$emit('hide');
  this.alert.success('2FA enabled successfully');
  this.reset();
}
```

---

## TOTP Settings Panel: `user/edit/vg-totp-settings.vue`

### Display Status

```vue
<div class="vg-totp-status">
  <p v-if="totpEnabled" class="text-success">
    ✓ Two-factor authentication is enabled
    <span class="text-muted">(Enabled on {{ formatDate(lastEnabled) }})</span>
  </p>
  <p v-else class="text-danger">
    ✗ Two-factor authentication is not enabled
  </p>
</div>
```

### Enable/Disable Actions

```vue
<button v-if="!totpEnabled" @click="showSetupModal = true">
  Enable 2FA
</button>

<template v-else>
  <button @click="showRegenerateModal = true">
    Regenerate Backup Codes
  </button>
  <button class="btn-danger" @click="showDisableModal = true">
    Disable 2FA
  </button>
</template>
```

### Disable Flow

```javascript
disableTotp() {
  this.request({
    method: 'POST',
    url: `/v1/users/${this.user.id}/totp/disable`,
    data: { password: this.confirmPassword },
    problemToAlert: ({ code }) => {
      if (code === 401.2) return 'Incorrect password';
      return null;
    }
  })
    .then(() => {
      this.alert.success('2FA has been disabled');
      this.showDisableModal = false;
      this.fetchStatus();  // Refresh UI
    });
}
```

### Regenerate Backup Codes

```javascript
regenerateBackupCodes() {
  this.request({
    method: 'POST',
    url: `/v1/users/${this.user.id}/totp/backup-codes/regenerate`,
    data: { password: this.regeneratePassword }
  })
    .then(({ data }) => {
      this.newBackupCodes = data.backupCodes;
      this.showBackupCodes = true;  // Display new codes
    });
}
```

---

## Error Handling

### Error Code Mapping

```javascript
const errorMessages = {
  '401.7': 'Invalid TOTP code. Please try again.',
  '401.2': 'Incorrect password.',
  '400.13': 'Backup code already used.',
  '429.1': 'Too many attempts. Please try again later.'
};

problemToAlert: (problem) => {
  return errorMessages[problem.code] || null;
}
```

### Error Recovery

| Error | User Action | Recovery |
|-------|------------|----------|
| Invalid code (401.7) | Retry TOTP | User re-enters code |
| Too many attempts (429.1) | Wait 10 minutes | Retry after timeout |
| Password incorrect (401.2) | Retry password | Ask for new password |
| Backup code used (400.13) | Use different code | Pick another backup code |

---

## State Management

### Session Resource

**File:** `/client/src/request-data/resources.js`

```javascript
createResource('session');  // Basic session resource
```

**Properties:**
- `session.data` - Session object or null
- `session.dataExists` - Boolean flag for UI reactivity
- `session.request()` - Fetch data and update automatically

### Session Data Structure

```javascript
{
  actorId: 5,
  token: "...",
  expiresAt: "2026-02-09T08:02:50Z",
  createdAt: "2026-02-08T08:02:50Z",
  csrf: "...",
  totp_verified: true,      // ← Check this on restore
  requireTotp: false        // ← Tells frontend if TOTP needed
}
```

---

## Testing

### Manual Testing Steps

#### 1. Setup 2FA
```
1. Navigate to Account Settings
2. Click "Enable 2FA"
3. Scan QR code with authenticator app
4. Enter 6-digit code from app
5. Save backup codes
6. Click "Enable 2FA"
7. Verify success message
```

#### 2. Login with 2FA
```
1. Log out
2. Enter email and password
3. See TOTP entry screen
4. Enter code from authenticator app
5. Verify login successful
6. Check that you're on dashboard
```

#### 3. Page Reload Protection
```
1. Enter password → See TOTP screen
2. Refresh page (don't enter TOTP code)
3. Verify redirected back to login
4. Enter password again
5. Enter TOTP code
6. Verify login successful
```

#### 4. Backup Codes
```
1. Click "Regenerate Backup Codes"
2. Enter password
3. See new backup codes
4. Copy/Download codes
5. Log out
6. Use backup code instead of TOTP
7. Verify login successful
```

### Browser DevTools Testing

```javascript
// Check session state
console.log(container.requestData.session.data);

// Check if TOTP required
console.log(response.data.requireTotp);
console.log(response.data.totp_verified);

// Check localStorage
console.log(localStorage.getItem('sessionExpires'));
```

---

## Common Issues & Solutions

### Issue: TOTP Screen Never Appears
**Cause:** `requireTotp` flag not being checked
**Fix:** Ensure response.data check includes `requireTotp`:
```javascript
if (response.data.requireTotp === true) {
  this.requiresTotp = true;
}
```

### Issue: Can Access App Without TOTP After Refresh
**Cause:** Session.data not cleared on restore
**Fix:** Ensure restoreSession() sets `session.data = null`:
```javascript
if (response.data.totp_verified === false) {
  session.data = null;  // ← Must do this
  removeSessionFromStorage();
}
```

### Issue: TOTP Code Not Accepted
**Cause:** Code expired (30-second window)
**Fix:** Get fresh code from authenticator app within 30 seconds

### Issue: Backup Codes Showing as Invalid
**Cause:** Code already used (single-use only)
**Fix:** Use a different backup code

---

## API Integration Checklist

- [ ] POST /v1/sessions returns `requireTotp` flag
- [ ] POST /v1/sessions/totp-verify endpoint implemented
- [ ] GET /v1/sessions/restore returns `totp_verified` field
- [ ] Frontend checks `totp_verified` on page reload
- [ ] Frontend shows TOTP screen when `requireTotp: true`
- [ ] Session.data cleared when TOTP not verified
- [ ] Error codes 401.7, 429.1 handled properly
- [ ] Preprocessor middleware rejects requests with `totp_verified: false`

---

## Related Documentation

- [TOTP API Contracts](TOTP_API_CONTRACTS.md)
- [Server-side TOTP Implementation](../vg-server/vg_api_TOTP.md)
- [IP Whitelist User Guide](vg_ip_whitelist_user_guide.md)

