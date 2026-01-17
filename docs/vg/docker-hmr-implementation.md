# HMR Client Implementation & Troubleshooting Guide

**Date**: 2026-01-17
**Status**: Implemented & Verified

This document details the technical challenges encountered and resolved while implementing the Dockerized Hot Module Replacement (HMR) workflow for ODK Central Frontend.

## 1. Build Context Permission Errors (`EACCES`)

### The Issue
When running `make dev` (or `docker compose build`), the build failed specifically on the `client` service with:
```
failed to solve: error from sender: open .../client/.nginx/client_body_temp: permission denied
```

### Root Cause
1.  **Volume Mounting**: The `client` container mounts the host's `client/` directory to `/usr/src/app`.
2.  **Nginx Runtime Files**: The Nginx process inside the `client` container runs as a non-root user (or configures paths relatively) and writes temporary files (`client_body_temp`, `proxy_temp`, etc.) into the mounted `.nginx/` directory.
3.  **Ownership Mismatch**: These files are created with `root` or `nobody` ownership.
4.  **Build Context**: When Docker attempts to build the image again, it scans the entire `client/` directory to create the build context. The build process (running as the host user) lacks read permissions for these root-owned temp files, causing the crash.

### The Fix
We created a **`.dockerignore`** file in the `client/` directory:

```gitignore
.git
.nginx        <-- CRITICAL
node_modules
dist
test
e2e-tests
```

**Why it works**: This instructs the Docker daemon to completely ignore the `.nginx` directory when assembling the build context. It prevents the read attempt entirely, bypassing the permission issue without needing `sudo` or permission modifications.

---

## 2. Nginx Startup Race Condition (Circular Dependency)

### The Issue
The `client` container would start, but Nginx would immediately crash (exit code 1) with:
```
[emerg] host not found in upstream "central.local" in .../main.nginx.conf
```
This caused a restart loop, preventing the dev server from coming up reliably.

### Root Cause
1.  **Startup Resolution**: Nginx, by default, attempts to resolve all hostnames defined in `proxy_pass` directives **at configuration load time** (startup).
2.  **Dependency Chain**: `client` depends on `nginx` (aliased as `central.local`).
3.  **Race Condition**: Even with `depends_on`, the `nginx` container might not be fully requested or the Docker DNS might not have propagated the `central.local` alias by the exact millisecond the `client` Nginx starts.
4.  **Fatal Error**: When Nginx cannot resolve an upstream hostname at startup, it treats it as a configuration error and refuses to start.

### The Fix
We modified `client/main.nginx.conf` to force **runtime (lazy) DNS resolution**.

**Before:**
```nginx
location ~ ^/v\d {
  proxy_pass https://central.local; # Resolved at startup (CRASH)
}
```

**After:**
```nginx
location ~ ^/v\d {
  # Use Docker's embedded DNS resolver
  resolver 127.0.0.11 valid=30s;
  
  # Set target as a variable
  set $backend_upstream https://central.local;
  
  # Proxy to the variable
  proxy_pass $backend_upstream; # Resolved at request time (SAFE)
}
```

**Why it works**:
- **`resolver 127.0.0.11`**: Explicitly tells Nginx to use Docker's internal DNS server.
- **Variable `proxy_pass`**: When `proxy_pass` is given a variable, Nginx cannot pre-resolve it. It is forced to look up the IP address only when a request actually hits that location block.
- **Result**: Nginx starts successfully even if `central.local` is offline. If a request comes in too early, it returns a 502/504 (Gateway Error) instead of crashing the entire process.

---

## 3. Host Port Conflicts

### The Issue
Original configs mapped Redis to host ports `6379` and `6380`. This conflicts with any local Redis instances developers might have running.

### The Fix
Updated `docker-compose.vg-dev.yml` to use obscure high-range ports:
- `enketo_redis_main`: `6379` -> `63799`
- `enketo_redis_cache`: `6380` -> `63800`

---

## 4. Simplified Command Workflow (Makefile)

To encapsulate the complexity of the multi-file compose command, a `Makefile` was introduced:

- **`make dev`**:
  `docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.vg-dev.yml up --detach --build`
- **`make stop`**:
  Stops the above stack.

This ensures developers always use the correct configuration layers without typing the full command.
