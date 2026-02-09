# VG Core Server File Edits

> **Purpose:** Document ALL modifications to upstream ODK Central core files
> **Critical:** Keep this updated for smooth upstream rebasing

---

## server/lib/model/query/vg-web-user-totp.js

**Status:** VG module file (NOT core upstream)

**Recent Changes:** 2026-02-09 - Service account exclusions

### Change: Exclude service accounts from TOTP enrollment

**Methods Modified:**
1. `isRoleMandatoryForTotp()` (lines 152-193)
2. `shouldPromptEnrollment()` (lines 200-241)

**Reason:** Service accounts are automated systems (CI/CD, bots) that cannot perform interactive 2FA verification. They rely on mandatory IP whitelist security instead.

**Implementation:**
- Added preliminary check for `users.is_service_account` column
- Returns `false` immediately if user is a service account
- Backwards-compatible: if column doesn't exist yet, treats all users as regular users
- No breaking changes to existing behavior

**Code Pattern:**
```javascript
// Check if service account first
maybeOne(sql`SELECT u.is_service_account FROM users u WHERE u."actorId" = ${actorId}`)
  .then((maybeUser) => {
    if (maybeUser.isDefined() && maybeUser.get().is_service_account === true) {
      return false;  // Skip enrollment for service accounts
    }
    // Continue with regular user logic...
  });
```

**Dependencies:**
- Column `users.is_service_account` will be added in future migration (service account security plan)
- Until then, query will fail gracefully (treated as regular user)

**Related Issues:**
- beads: central-7oo, central-g1f
- Plan: `/plan/service-account-security-v2.md`
- Analysis: `/plan/enrollment-vs-service-accounts-analysis.md`

---

## server/lib/resources/sessions.js

**Status:** Core upstream file (MODIFIED)

**Recent Changes:** 2026-02-09 - TOTP enrollment flow integration

### Change: Add enrollment detection to POST /v1/sessions

**Location:** Lines 149-182 (POST endpoint handler)

**Reason:** Implement optional and mandatory TOTP enrollment flows at login time. Users in mandatory roles must set up 2FA before accessing the system, while other users receive dismissible prompts.

**Implementation:**
- After successful password authentication, check if user needs TOTP enrollment
- For mandatory roles (e.g., admin):
  - Return temporary session without cookies
  - Set `requireTotpSetup: true` and `mandatory: true` flags
  - Session expires in 5 minutes
  - User must complete setup before full access
- For non-mandatory roles:
  - Create full session with cookies  - Add `shouldPromptTotpEnrollment` flag if user should be prompted
  - User can dismiss prompt (temporary or permanent)
- Service accounts excluded from all enrollment checks

**Code Pattern:**
```javascript
// Check if mandatory enrollment required
return VgWebUserTotp.isRoleMandatoryForTotp(user.actorId)
  .then((isMandatory) => {
    if (isMandatory) {
      // Create temporary session for setup (no cookies)
      return Promise.all([
        createUserSession({ Audits, Sessions, Users }, headers, user, false),
        resolve(response)
      ])
        .then(([ session ]) => ({
          ...session,
          requireTotpSetup: true,
          mandatory: true
        }));
    }

    // Not mandatory - create full session with cookies
    return createUserSession({ Audits, Sessions, Users }, headers, user, true)
      .then((middleware) => middleware(_, response))
      .then((sessionResult) => {
        // Add optional enrollment prompt flag
        return VgWebUserTotp.shouldPromptEnrollment(user.actorId)
          .then((shouldPrompt) => ({
            ...sessionResult,
            shouldPromptTotpEnrollment: shouldPrompt
          }));
      });
  });
```

**Related Files:**
- `lib/model/query/vg-web-user-totp.js` - Enrollment logic
- `lib/resources/vg-web-user-totp.js` - TOTP endpoints
- `lib/resources/vg-settings.js` - Mandatory roles configuration

**Dependencies:**
- `vg_settings.vg_totp_mandatory_roles` setting (JSON array)
- `users.totp_prompt_remind_after` column
- `users.totp_prompt_dismissed_at` column
- `users.is_service_account` column

**Related Issues:**
- beads: central-tbg (documentation), central-mox (service accounts)

---

## Future Core File Edits (Planned)

### server/lib/http/preprocessors.js (Planned)
**Changes:** API token authentication detection, service account IP whitelist enforcement
**Status:** Not yet implemented

### server/lib/resources/sessions.js (Planned)
**Changes:** 1-hour session lifetime for service accounts
**Status:** Not yet implemented

---

## Rebase Strategy

When rebasing onto upstream:
1. **Check for conflicts** in these files first
2. **Preserve VG changes** (minimal and well-documented)
3. **Test enrollment flows** after rebase
4. **Update this doc** if line numbers change
