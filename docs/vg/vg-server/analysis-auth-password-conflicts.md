# Auth/Password Conflicts Analysis

**Analysis Date:** 2026-01-12
**Task:** central-xav.4 (P1.2)
**Risk Level:** LOW (Mostly Compatible)
**Conflict Complexity:** MINIMAL

---

## Executive Summary

**GOOD NEWS:** VG and upstream password validation are highly compatible with minimal conflicts.

**Key Findings:**
- ✅ **No core crypto.js conflicts** - VG hasn't modified password hashing
- ✅ **Compatible validation** - Both enforce min 10 chars, VG adds complexity on top
- ✅ **VG policy is isolated** - Only used in VG-specific code (`vg-app-user-auth.js`)
- ⚠️ **One enhancement needed** - VG should adopt upstream's 72-byte limit
- ⚠️ **getAnyPasswordHash removed** - Timing attack mitigation (covered in session analysis)

---

## Upstream Password Changes

### PR #1389: Reject Passwords > 72 Bytes

**Motivation:**
bcrypt silently truncates passwords longer than 72 bytes, which is misleading to users. Upstream now explicitly rejects such passwords.

**Change in `lib/util/crypto.js`:**
```javascript
const hashPassword = (plain) => {
  if (typeof plain !== 'string')
    return reject(Problem.user.invalidDataTypeOfParameter({ value: plain, expected: 'string' }));
  if (plain.length < 10) return reject(Problem.user.passwordTooShort());
  if (plain.length > 72) return reject(Problem.user.passwordTooLong());  // NEW
  return isBlank(plain) ? resolve(null) : bcrypt.hash(plain, BCRYPT_COST_FACTOR);
};
```

**Impact:**
- Enforces minimum 10 characters (unchanged)
- **NEW:** Enforces maximum 72 bytes (bcrypt technical limitation)
- Clearer error messages for users

### PR #1410 & #1411: Standardize Password Error Responses

**Changes:**
- Standardized error messages for invalid existing passwords
- Standardized error messages for invalid new passwords
- Consistent error handling across password operations

**Impact:**
- Better user experience
- Consistent API responses
- No breaking changes

### PR #1408: Document bcrypt Implementation Curiosity

**Changes:**
- Documentation about bcrypt behavior
- Notes on 72-byte limitation
- API documentation updates

**Impact:**
- No code changes
- Improved documentation

---

## VG Password Policy

### Implementation: `lib/util/vg-password.js`

**VG Password Requirements:**
```javascript
const policy = {
  minLength: 10,                          // Same as upstream
  special: /[~!@#$%^&*()_+\-=,.]/,       // VG addition
  upper: /[A-Z]/,                         // VG addition
  lower: /[a-z]/,                         // VG addition
  digit: /[0-9]/                          // VG addition
};

const validateVgPassword = (password) => {
  if (typeof password !== 'string') return false;
  return password.length >= policy.minLength
    && policy.special.test(password)
    && policy.upper.test(password)
    && policy.lower.test(password)
    && policy.digit.test(password);
};
```

**Complexity Requirements:**
- **Minimum length:** 10 characters (matches upstream)
- **Uppercase letter:** At least one (A-Z)
- **Lowercase letter:** At least one (a-z)
- **Digit:** At least one (0-9)
- **Special character:** At least one from `~!@#$%^&*()_+-=,.`

### Usage: `lib/domain/vg-app-user-auth.js`

VG password validation is only used in VG-specific app user authentication:

```javascript
// Line 4
const { validateVgPassword } = require('../util/vg-password');

// Lines 46-49
const ensurePasswordPolicy = (password) => {
  if (!validateVgPassword(password))
    throw Problem.user.passwordWeak();
};
```

**Called from:**
- App user password reset
- App user password change
- App user creation (if password provided)

**NOT used for:**
- Web user passwords (uses upstream validation only)
- Field key passwords
- OIDC authentication

---

## Compatibility Analysis

### Layering Strategy

VG password policy is **layered on top** of upstream validation:

```
User submits password
        ↓
1. VG: ensurePasswordPolicy(password)
   ├─ Check min 10 chars
   ├─ Check uppercase
   ├─ Check lowercase
   ├─ Check digit
   └─ Check special char
        ↓
2. Upstream: hashPassword(password)
   ├─ Check typeof string
   ├─ Check min 10 chars  ✅ (redundant but harmless)
   ├─ Check max 72 bytes  🆕 (NEW from upstream)
   └─ bcrypt.hash()
        ↓
   Password stored
```

### Compatibility Matrix

| Check | Upstream | VG | Conflict? | Resolution |
|-------|----------|-----|-----------|------------|
| **Type string** | ✅ | ✅ | No | Both check |
| **Min 10 chars** | ✅ | ✅ | No | Both enforce |
| **Max 72 bytes** | ✅ | ❌ | **Minor** | VG should add |
| **Uppercase** | ❌ | ✅ | No | VG adds on top |
| **Lowercase** | ❌ | ✅ | No | VG adds on top |
| **Digit** | ❌ | ✅ | No | VG adds on top |
| **Special char** | ❌ | ✅ | No | VG adds on top |

**Verdict:** ✅ **Fully compatible** with one enhancement needed (72-byte check).

---

## File-by-File Analysis

### 1. lib/util/crypto.js

**VG Changes:** NONE
**Upstream Changes:** Added 72-byte limit check
**Conflict:** NONE

**Resolution:**
- Accept upstream changes (no merge needed, VG hasn't modified this file)

---

### 2. lib/util/vg-password.js

**VG Changes:** NEW FILE (VG-only)
**Upstream Changes:** N/A (file doesn't exist upstream)
**Conflict:** NONE

**Enhancement Needed:**
Add 72-byte check to VG password validation:

```javascript
const validateVgPassword = (password) => {
  if (typeof password !== 'string') return false;
  if (password.length > 72) return false;  // NEW: Align with upstream bcrypt limit
  return password.length >= policy.minLength
    && policy.special.test(password)
    && policy.upper.test(password)
    && policy.lower.test(password)
    && policy.digit.test(password);
};
```

**Rationale:**
- Aligns VG with upstream bcrypt behavior
- Prevents misleading users (bcrypt truncates at 72 bytes)
- Provides clearer error message earlier in validation chain

---

### 3. lib/domain/vg-app-user-auth.js

**VG Changes:** NEW FILE (VG-only)
**Upstream Changes:** N/A (file doesn't exist upstream)
**Conflict:** NONE

**Resolution:**
- No changes needed
- File is VG-specific, won't conflict with upstream

---

### 4. lib/model/query/users.js

**VG Changes:** KEPT `getAnyPasswordHash()` function
**Upstream Changes:** REMOVED `getAnyPasswordHash()` function
**Conflict:** YES (covered in session management analysis)

**Diff:**
```javascript
// VG KEEPS (lines 91-99):
const getAnyPasswordHash = () => ({ maybeOne }) =>
  maybeOne(sql`
    select users.password
    from users
    join actors on users."actorId"=actors.id
    where users.password is not null
      and actors."deletedAt" is null
    limit 1
  `).then((opt) => opt.map((row) => row.password).orNull());

// VG KEEPS in exports (line 105):
module.exports = {
  ...
  getAnyPasswordHash  // VG addition
};
```

**Usage:**
- Used in `lib/resources/sessions.js:94` for timing attack mitigation
- Part of VG login hardening feature

**Resolution:**
- Keep `getAnyPasswordHash()` function in VG fork
- Required for VG login hardening (see session management analysis)
- Documented in `analysis-session-management-conflicts.md`

---

### 5. lib/resources/users.js

**VG Changes:** NONE (checked, no differences)
**Upstream Changes:** Unknown (no significant diff)
**Conflict:** NONE

**Resolution:**
- Accept upstream changes (no merge needed)

---

## Problem Codes

### Upstream Problem Codes

From `lib/util/crypto.js`:
```javascript
Problem.user.invalidDataTypeOfParameter({ value: plain, expected: 'string' })
Problem.user.passwordTooShort()
Problem.user.passwordTooLong()  // NEW
```

### VG Problem Codes

From `lib/domain/vg-app-user-auth.js`:
```javascript
Problem.user.passwordWeak()  // VG addition
```

**Compatibility:**
- ✅ No conflicts
- VG adds new problem code for weak passwords (complexity requirements)
- Upstream adds new problem code for too-long passwords
- Different error codes, different use cases

---

## Testing Strategy

### Pre-Rebase Baseline

Capture current password validation behavior:

```bash
# VG password validation unit tests
npx mocha test/unit/util/vg-password.js

# App user password tests
npx mocha test/integration/api/vg-app-user-auth.js --grep "password"

# Web user password tests
npx mocha test/integration/api/users.js --grep "password"
```

### Post-Rebase Validation

Test these scenarios:

**VG App User Passwords:**
- [ ] Min 10 chars enforced
- [ ] Max 72 bytes enforced (after VG enhancement)
- [ ] Uppercase required
- [ ] Lowercase required
- [ ] Digit required
- [ ] Special char required
- [ ] Error message: `passwordWeak` for complexity failures
- [ ] Error message: `passwordTooLong` for > 72 bytes

**Web User Passwords (Upstream):**
- [ ] Min 10 chars enforced
- [ ] Max 72 bytes enforced
- [ ] No complexity requirements (upstream default)
- [ ] Error message: `passwordTooShort` for < 10 chars
- [ ] Error message: `passwordTooLong` for > 72 bytes

**Password Hashing:**
- [ ] bcrypt still works for both app users and web users
- [ ] Hashed passwords can be verified
- [ ] No regressions in authentication flows

---

## Rebase Strategy

### Phase 1: Accept Upstream Changes

**Step 1:** Accept upstream `crypto.js`
```bash
git checkout upstream/master -- lib/util/crypto.js
# No merge needed - VG hasn't modified this file
```

**Step 2:** Accept upstream `users.js`
```bash
git checkout upstream/master -- lib/model/query/users.js
# Then re-add getAnyPasswordHash() for VG login hardening
```

### Phase 2: Enhance VG Password Validation

**Step 3:** Update `lib/util/vg-password.js`

Add 72-byte check:
```javascript
const validateVgPassword = (password) => {
  if (typeof password !== 'string') return false;
  if (password.length > 72) return false;  // NEW
  return password.length >= policy.minLength
    && policy.special.test(password)
    && policy.upper.test(password)
    && policy.lower.test(password)
    && policy.digit.test(password);
};
```

**Step 4:** Update tests

Add test case for 72-byte limit:
```javascript
// test/unit/util/vg-password.js
it('should reject passwords longer than 72 bytes', () => {
  const longPassword = 'A'.repeat(73) + '1!';  // 75 chars, > 72 bytes
  validateVgPassword(longPassword).should.equal(false);
});
```

### Phase 3: Re-add getAnyPasswordHash()

**Step 5:** Restore VG's timing attack mitigation

In `lib/model/query/users.js`:
```javascript
const getAnyPasswordHash = () => ({ maybeOne }) =>
  maybeOne(sql`
    select users.password
    from users
    join actors on users."actorId"=actors.id
    where users.password is not null
      and actors."deletedAt" is null
    limit 1
  `).then((opt) => opt.map((row) => row.password).orNull());

module.exports = {
  ...
  getAnyPasswordHash  // Re-add to exports
};
```

### Phase 4: Testing

Run all password-related tests:
```bash
# Unit tests
npx mocha test/unit/util/vg-password.js

# Integration tests
npx mocha test/integration/api/vg-app-user-auth.js --grep "password"
npx mocha test/integration/api/users.js --grep "password"
npx mocha test/integration/api/sessions.js
```

---

## Risk Assessment

### Low Risk Areas

1. **VG Password Policy (`vg-password.js`)**
   - Risk: MINIMAL
   - Reason: VG-only file, no upstream equivalent
   - Mitigation: Enhancement (72-byte check) is additive, low risk

2. **Core Password Hashing (`crypto.js`)**
   - Risk: MINIMAL
   - Reason: VG hasn't modified this file
   - Mitigation: Accept upstream changes, no merge needed

3. **VG Domain Logic (`vg-app-user-auth.js`)**
   - Risk: MINIMAL
   - Reason: VG-only file, no upstream equivalent
   - Mitigation: No changes needed, no conflicts

### Medium Risk Areas

1. **getAnyPasswordHash() in users.js**
   - Risk: MEDIUM
   - Reason: Upstream removed, VG uses for timing attack mitigation
   - Mitigation: Re-add after accepting upstream changes
   - Fallback: Remove and simplify login flow (less secure)

### No High Risk Areas

All auth/password conflicts are low-to-medium risk with clear resolution paths.

---

## Enhancement Recommendations

### 1. Adopt 72-Byte Limit in VG Password Policy

**Priority:** HIGH
**Effort:** LOW (5 minutes)
**Impact:** Aligns VG with upstream, prevents user confusion

**Implementation:**
```javascript
// lib/util/vg-password.js
const validateVgPassword = (password) => {
  if (typeof password !== 'string') return false;
  if (password.length > 72) return false;  // NEW
  return password.length >= policy.minLength
    && policy.special.test(password)
    && policy.upper.test(password)
    && policy.lower.test(password)
    && policy.digit.test(password);
};
```

### 2. Update VG Password Policy Documentation

**Priority:** MEDIUM
**Effort:** LOW (10 minutes)
**Impact:** Clearer user guidance

**Add to documentation:**
- Password must be 10-72 characters
- Must include uppercase, lowercase, digit, special character
- bcrypt technical limitation (72 bytes)

### 3. Add Error Message for 72-Byte Limit

**Priority:** LOW
**Effort:** LOW (5 minutes)
**Impact:** Better user experience

**Implementation:**
```javascript
// lib/domain/vg-app-user-auth.js
const ensurePasswordPolicy = (password) => {
  if (password.length > 72)
    throw Problem.user.passwordTooLong();  // Use upstream error
  if (!validateVgPassword(password))
    throw Problem.user.passwordWeak();
};
```

---

## Testing Checklist

### VG App User Password Validation

Test with these passwords:

| Password | Expected Result | Reason |
|----------|-----------------|--------|
| `short` | ❌ REJECT | < 10 chars |
| `ValidPass1!` | ✅ ACCEPT | Meets all requirements |
| `A` * 73 + `1!` | ❌ REJECT | > 72 bytes |
| `alllowercase1!` | ❌ REJECT | No uppercase |
| `ALLUPPERCASE1!` | ❌ REJECT | No lowercase |
| `NoDigitsHere!` | ❌ REJECT | No digit |
| `NoSpecialChar1` | ❌ REJECT | No special char |
| `P@ssw0rd123` | ✅ ACCEPT | Meets all requirements |

### Web User Password Validation

Test with these passwords:

| Password | Expected Result | Reason |
|----------|-----------------|--------|
| `short` | ❌ REJECT | < 10 chars |
| `valid_pass_10` | ✅ ACCEPT | >= 10 chars (no complexity required) |
| `A` * 73 | ❌ REJECT | > 72 bytes |
| `no_uppercase_only` | ✅ ACCEPT | No complexity required for web users |

### Password Hashing

- [ ] bcrypt.hash() works for 10-72 char passwords
- [ ] bcrypt.compare() verifies hashed passwords
- [ ] hashPassword() rejects < 10 chars
- [ ] hashPassword() rejects > 72 bytes
- [ ] hashPassword() accepts valid passwords

---

## Rollback Plan

If password validation breaks after rebase:

```bash
# Restore VG files
git checkout vg-work-pre-rebase-2025.4.0 -- lib/util/vg-password.js
git checkout vg-work-pre-rebase-2025.4.0 -- lib/domain/vg-app-user-auth.js

# Restore users.js with getAnyPasswordHash
git checkout vg-work-pre-rebase-2025.4.0 -- lib/model/query/users.js

# Re-run tests
npx mocha test/unit/util/vg-password.js
npx mocha test/integration/api/vg-app-user-auth.js --grep "password"

# Commit rollback
git add lib/util/vg-password.js lib/domain/vg-app-user-auth.js lib/model/query/users.js
git commit -m "Rollback: Restore VG password validation (rebase conflict resolution failed)"
```

---

## Summary

**Conflict Level:** ✅ **LOW** (Minimal, easily resolved)

**Key Actions:**
1. Accept upstream `crypto.js` (no VG modifications)
2. Enhance VG password policy with 72-byte check
3. Re-add `getAnyPasswordHash()` to users.js (for login hardening)
4. Run comprehensive password validation tests

**Compatibility:** ✅ **EXCELLENT** - VG policy layers on top of upstream with no structural conflicts

**Risk:** ✅ **LOW** - All conflicts have clear, low-risk resolution paths

**Recommendation:** Proceed with rebase, apply enhancements, test thoroughly.

---

## References

- **Upstream PRs:**
  - #1389: bcrypt: reject passwords > 72 bytes
  - #1410: Standardise responses for invalid existing passwords
  - #1411: Standardise responses for invalid new passwords
  - #1408: api/sessions: document bcrypt implementation curiosity

- **VG Files:**
  - `lib/util/vg-password.js` (19 lines)
  - `lib/domain/vg-app-user-auth.js` (uses VG policy)
  - `lib/model/query/users.js` (getAnyPasswordHash function)

- **Related Analysis:**
  - `analysis-session-management-conflicts.md` (getAnyPasswordHash usage)
  - `pre-rebase-state-v2024.3.1.md` (current VG state)
  - `rebase-v2025.4.0-plan.md` (overall rebase plan)

---

**Analysis Status:** Complete
**Next Task:** P1.3 - Analyze database migration conflicts
**Recommendation:** ✅ Proceed - Low risk, clear resolution path
