# VG App User Auth - User Behavior

> **Last Updated**: 2026-01-02

This document describes all user-visible behavior changes introduced by VG app-user auth.

## Roles and permissions

- Project admins/managers can create/update app users, reset passwords, revoke sessions, and activate/deactivate.
- App users can only log in for tokens, change their own password, and revoke their own sessions.
- App users cannot log in to the Central web UI.

## Login and sessions

- App users log in with username/password via the app-user login endpoint.
- Login uses the username (not display name).
- Login returns a short-lived bearer token; tokens are not returned by create/list endpoints.
- Tokens expire at `expiresAt` (no sliding refresh) and must be used in `Authorization: Bearer <token>`.
- Tokens are bearer-only; cookies are ignored for these routes.
- App users are project-scoped; login returns `projectId` for the linked field key.
- App user login requests include `deviceId` and optional `comments` to identify the device/session.

## App user creation and updates

- Creation requires `username` and `password` (in addition to display name).
- Updates allow display name and phone changes; activation/deactivation uses the dedicated endpoint; password changes use the dedicated endpoint.
- Create/list responses never return long-lived tokens (`token` is always null in listings).

## Session cap behavior

- Each app user has a maximum number of active sessions (default 3).
- When a new login exceeds the cap, the oldest sessions are automatically revoked.

## Password policy

- Minimum 10 characters.
- At least one uppercase, one lowercase, one digit, one special (`~!@#$%^&*()_+-=,.`).

## Login throttling and lockouts

- Defaults: 5 failed attempts in 5 minutes per username+IP triggers a 10-minute lock.
- Project overrides can be set via `vg_project_settings` for max failures, window minutes, and duration minutes.
- Attempts are tracked server-side for lockout enforcement.
- Lockouts are recorded in `vg_app_user_lockouts`.
- Project mismatch logins count as failed attempts for lockout tracking.
- Admins can clear app-user lockouts via `POST /system/app-users/lockouts/clear` (optionally scoped by IP).

## Activation and revocation

- Deactivating an app user immediately revokes existing sessions.
- Deactivated users cannot authenticate until reactivated.
- Admins (web UI) can revoke all sessions for an app user; app users can revoke only the current session.
- Admins can view active sessions with IP/device/comment metadata.

## Telemetry

- App users can send device telemetry (deviceId, Collect version, device timestamp, and full location params).
- Telemetry records store both device generation time (`deviceDateTime`) and server receive time (`dateTime`).
- Only app users can submit telemetry; web users cannot submit on their behalf.
- System admins can review telemetry with filters by projectId, appUserId, deviceId, and date range.
- Telemetry records are retained indefinitely (no TTL cleanup).

## App user fields

- App users now include `username` and optional `phone`.
- Username is required, normalized to lowercase, and treated as immutable after creation.
- Phone is optional, trimmed, and capped at 25 characters.
- New app users are active by default unless explicitly deactivated.
