#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

# ============================================================================
# Colors and logging
# ============================================================================

if tput colors &>/dev/null; then
  BOLD='\033[1m'
  BLUE='\033[34m'
  GREEN='\033[32m'
  YELLOW='\033[33m'
  RED='\033[31m'
  RESET='\033[0m'
else
  BOLD=''
  BLUE=''
  GREEN=''
  YELLOW=''
  RED=''
  RESET=''
fi

log() { echo >&2 -e "${BLUE}[doctor]${RESET} $*"; }
ok() { echo >&2 -e "${GREEN}✓${RESET} $*"; }
warn() { echo >&2 -e "${YELLOW}⚠${RESET} $*"; }
err() { echo >&2 -e "${RED}✗${RESET} $*"; }
section() { echo >&2 ""; echo >&2 -e "${BOLD}${1}${RESET}"; }

ERROR_COUNT=0
WARNING_COUNT=0

# ============================================================================
# Helper functions
# ============================================================================

dc() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    return 1
  fi
}

check_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    err "Docker is not installed or not in PATH"
    ((ERROR_COUNT++))
    return 1
  fi
  ok "Docker is installed"

  if ! docker info >/dev/null 2>&1; then
    err "Docker daemon is not running"
    ((ERROR_COUNT++))
    return 1
  fi
  ok "Docker daemon is running"

  if ! dc version >/dev/null 2>&1; then
    err "Docker Compose is not available"
    ((ERROR_COUNT++))
    return 1
  fi
  ok "Docker Compose is available"
  return 0
}

check_env_file() {
  if [ ! -f ".env" ]; then
    err ".env file not found. Run: ./scripts/init-odk.sh"
    ((ERROR_COUNT++))
    return 1
  fi
  ok ".env file exists"

  # Load .env
  set +u
  source .env 2>/dev/null || true
  set -u

  # Check required variables
  local missing=()
  [ -z "${DOMAIN:-}" ] && missing+=("DOMAIN")
  [ -z "${SYSADMIN_EMAIL:-}" ] && missing+=("SYSADMIN_EMAIL")
  [ -z "${SSL_TYPE:-}" ] && missing+=("SSL_TYPE")

  if [ ${#missing[@]} -gt 0 ]; then
    err "Missing required .env variables: ${missing[*]}"
    ((ERROR_COUNT++))
    return 1
  fi
  ok "Required .env variables are set"

  # Validate SSL_TYPE
  case "${SSL_TYPE:-}" in
    letsencrypt|customssl|upstream|selfsign)
      ok "SSL_TYPE is valid: ${SSL_TYPE}"
      ;;
    *)
      err "Invalid SSL_TYPE: ${SSL_TYPE} (must be: letsencrypt, customssl, upstream, or selfsign)"
      ((ERROR_COUNT++))
      ;;
  esac

  # Check port configuration
  if [ "${SSL_TYPE:-}" = "upstream" ]; then
    if [ "${HTTP_PORT:-80}" != "8080" ] || [ "${HTTPS_PORT:-443}" != "8443" ]; then
      warn "SSL_TYPE=upstream usually requires HTTP_PORT=8080 and HTTPS_PORT=8443"
      ((WARNING_COUNT++))
    fi
  elif [ "${SSL_TYPE:-}" = "letsencrypt" ]; then
    if [ "${HTTP_PORT:-80}" != "80" ] || [ "${HTTPS_PORT:-443}" != "443" ]; then
      err "SSL_TYPE=letsencrypt requires HTTP_PORT=80 and HTTPS_PORT=443"
      ((ERROR_COUNT++))
    fi
  fi

  # Check domain validity
  if [ "${SSL_TYPE:-}" = "letsencrypt" ]; then
    if [[ "${DOMAIN:-}" == *.local ]] || [[ "${DOMAIN:-}" == localhost ]]; then
      err "SSL_TYPE=letsencrypt cannot work with local domain: ${DOMAIN}"
      ((ERROR_COUNT++))
    fi
  fi

  return 0
}

check_s3_config() {
  set +u
  source .env 2>/dev/null || true
  set -u

  local s3_vars_set=0
  [ -n "${S3_SERVER:-}" ] && ((s3_vars_set++))
  [ -n "${S3_BUCKET_NAME:-}" ] && ((s3_vars_set++))
  [ -n "${S3_ACCESS_KEY:-}" ] && ((s3_vars_set++))
  [ -n "${S3_SECRET_KEY:-}" ] && ((s3_vars_set++))

  if [ $s3_vars_set -eq 0 ]; then
    warn "S3 not configured (blobs will be stored in PostgreSQL)"
    ((WARNING_COUNT++))
    return 0
  fi

  if [ $s3_vars_set -ne 4 ]; then
    err "Partial S3 configuration (need all 4: S3_SERVER, S3_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_KEY)"
    ((ERROR_COUNT++))
    return 1
  fi

  ok "S3 configuration is complete"

  # Check Garage-specific config
  if [ "${VG_GARAGE_ENABLED:-false}" = "true" ]; then
    if [ ! -f "docker-compose-garage.yml" ]; then
      err "VG_GARAGE_ENABLED=true but docker-compose-garage.yml not found"
      ((ERROR_COUNT++))
      return 1
    fi
    if [ ! -f "garage/garage.toml" ]; then
      err "VG_GARAGE_ENABLED=true but garage/garage.toml not found"
      ((ERROR_COUNT++))
      return 1
    fi
    ok "Garage configuration files exist"
  fi

  return 0
}

check_db_config() {
  set +u
  source .env 2>/dev/null || true
  set -u

  if [ -n "${DB_HOST:-}" ]; then
    # External DB
    local missing=()
    [ -z "${DB_USER:-}" ] && missing+=("DB_USER")
    [ -z "${DB_PASSWORD:-}" ] && missing+=("DB_PASSWORD")
    [ -z "${DB_NAME:-}" ] && missing+=("DB_NAME")

    if [ ${#missing[@]} -gt 0 ]; then
      err "External DB configured but missing: ${missing[*]}"
      ((ERROR_COUNT++))
      return 1
    fi
    ok "External database configuration is complete"
  else
    ok "Using containerized database (default)"
  fi

  return 0
}

check_networks() {
  # Check what docker-compose.yml expects
  local expected_networks=()
  if grep -q "name: central_db_net" docker-compose.yml 2>/dev/null; then
    expected_networks+=("central_db_net" "central_web")
  else
    expected_networks+=("db_net" "web")
  fi

  # If containers are running, check what they're actually using
  if docker ps --format '{{.Names}}' | grep -q 'central-service-1' 2>/dev/null; then
    local actual_networks
    actual_networks="$(docker inspect central-service-1 --format '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' 2>/dev/null || true)"

    if echo "$actual_networks" | grep -qE "(db_net|central_db_net)"; then
      ok "Docker networks are configured and in use"
      return 0
    fi
  fi

  # Fall back to checking expected networks
  local missing=()
  for net in "${expected_networks[@]}"; do
    if ! docker network inspect "$net" >/dev/null 2>&1; then
      missing+=("$net")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    # Check if the alternative naming exists
    local alt_missing=()
    if [[ "${expected_networks[0]}" == "central_db_net" ]]; then
      # Expected central_* but check if db_net/web exist
      docker network inspect "db_net" >/dev/null 2>&1 || alt_missing+=("db_net")
      docker network inspect "web" >/dev/null 2>&1 || alt_missing+=("web")

      if [ ${#alt_missing[@]} -eq 0 ]; then
        warn "Networks exist as 'db_net' and 'web' but docker-compose.yml expects 'central_db_net' and 'central_web'"
        log "Either rename networks or update docker-compose.yml"
        ((WARNING_COUNT++))
        return 0
      fi
    fi

    err "Missing Docker networks: ${missing[*]}"
    log "Create them with:"
    for net in "${missing[@]}"; do
      log "  docker network create $net"
    done
    ((ERROR_COUNT++))
    return 1
  fi
  ok "Required Docker networks exist"
  return 0
}

check_submodules() {
  local missing=()

  # Check if .git exists (can be file or directory) and if key files exist
  if [ ! -e "client/.git" ] || [ ! -f "client/package.json" ]; then
    missing+=("client")
  fi

  if [ ! -e "server/.git" ] || [ ! -f "server/package.json" ]; then
    missing+=("server")
  fi

  if [ ${#missing[@]} -gt 0 ]; then
    err "Missing or uninitialized submodules: ${missing[*]}"
    log "Initialize with: git submodule update --init --recursive"
    ((ERROR_COUNT++))
    return 1
  fi
  ok "Submodules are initialized"
  return 0
}

check_port_conflicts() {
  set +u
  source .env 2>/dev/null || true
  set -u

  local http_port="${HTTP_PORT:-80}"
  local https_port="${HTTPS_PORT:-443}"
  local conflicts=()

  # Check if ports are already bound (excluding Docker)
  if command -v lsof >/dev/null 2>&1; then
    if lsof -Pi :${http_port} -sTCP:LISTEN -t >/dev/null 2>&1; then
      local proc
      proc="$(lsof -Pi :${http_port} -sTCP:LISTEN | tail -n 1 | awk '{print $1}')"
      if [[ "$proc" != "docker"* ]] && [[ "$proc" != "com.docke"* ]]; then
        conflicts+=("${http_port} (used by $proc)")
      fi
    fi
    if lsof -Pi :${https_port} -sTCP:LISTEN -t >/dev/null 2>&1; then
      local proc
      proc="$(lsof -Pi :${https_port} -sTCP:LISTEN | tail -n 1 | awk '{print $1}')"
      if [[ "$proc" != "docker"* ]] && [[ "$proc" != "com.docke"* ]]; then
        conflicts+=("${https_port} (used by $proc)")
      fi
    fi
  fi

  if [ ${#conflicts[@]} -gt 0 ]; then
    warn "Port conflicts detected: ${conflicts[*]}"
    ((WARNING_COUNT++))
    return 0
  fi
  ok "No port conflicts detected"
  return 0
}

check_containers() {
  if ! docker ps >/dev/null 2>&1; then
    warn "Cannot check container status (Docker not accessible)"
    ((WARNING_COUNT++))
    return 0
  fi

  local running_containers
  running_containers="$(docker ps --format '{{.Names}}' 2>/dev/null || true)"

  if [ -z "$running_containers" ]; then
    warn "No ODK Central containers are running"
    log "Start them with: docker compose up -d"
    ((WARNING_COUNT++))
    return 0
  fi

  # Check for key containers
  local key_containers=("central-service-1" "central-nginx-1")
  local missing=()

  for container in "${key_containers[@]}"; do
    if ! echo "$running_containers" | grep -q "^${container}$"; then
      missing+=("$container")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    warn "Key containers not running: ${missing[*]}"
    ((WARNING_COUNT++))
  else
    ok "Key containers are running"
  fi

  # Check container health
  local unhealthy
  unhealthy="$(docker ps --filter health=unhealthy --format '{{.Names}}' 2>/dev/null || true)"
  if [ -n "$unhealthy" ]; then
    err "Unhealthy containers detected: $unhealthy"
    ((ERROR_COUNT++))
  fi

  return 0
}

check_garage_runtime() {
  set +u
  source .env 2>/dev/null || true
  set -u

  if [ "${VG_GARAGE_ENABLED:-false}" != "true" ]; then
    return 0
  fi

  if ! docker ps --format '{{.Names}}' | grep -q '^odk-garage$'; then
    warn "Garage is enabled but container 'odk-garage' is not running"
    log "Start it with: docker compose -f docker-compose.yml -f docker-compose-garage.yml up -d garage"
    ((WARNING_COUNT++))
    return 0
  fi
  ok "Garage container is running"

  # Check if Garage is responding
  if docker exec odk-garage /garage status >/dev/null 2>&1; then
    ok "Garage is responding to commands"
  else
    err "Garage container is running but not responding"
    log "Check logs: docker logs odk-garage"
    ((ERROR_COUNT++))
  fi

  return 0
}

check_db_connectivity() {
  set +u
  source .env 2>/dev/null || true
  set -u

  local db_host="${DB_HOST:-postgres14}"

  if [ "$db_host" = "postgres14" ]; then
    # Container DB
    if ! docker ps --format '{{.Names}}' | grep -q 'postgres14'; then
      warn "PostgreSQL container is not running"
      ((WARNING_COUNT++))
      return 0
    fi
    ok "PostgreSQL container is running"
  else
    # External DB - skip runtime check
    warn "External DB configured - skipping connectivity check"
    ((WARNING_COUNT++))
  fi

  return 0
}

check_file_permissions() {
  local problem_dirs=()

  # Check if we can write to key directories
  for dir in "files" "garage" "."; do
    if [ -d "$dir" ]; then
      if [ ! -w "$dir" ]; then
        problem_dirs+=("$dir")
      fi
    fi
  done

  if [ ${#problem_dirs[@]} -gt 0 ]; then
    warn "Write permission issues in: ${problem_dirs[*]}"
    ((WARNING_COUNT++))
    return 0
  fi
  ok "File permissions look good"
  return 0
}

check_ssl_files() {
  set +u
  source .env 2>/dev/null || true
  set -u

  case "${SSL_TYPE:-}" in
    customssl)
      if [ ! -d "files/local/customssl" ]; then
        err "SSL_TYPE=customssl but files/local/customssl directory not found"
        ((ERROR_COUNT++))
        return 1
      fi
      local missing=()
      [ ! -f "files/local/customssl/fullchain.pem" ] && missing+=("fullchain.pem")
      [ ! -f "files/local/customssl/privkey.pem" ] && missing+=("privkey.pem")

      if [ ${#missing[@]} -gt 0 ]; then
        err "SSL_TYPE=customssl but missing certificate files: ${missing[*]}"
        ((ERROR_COUNT++))
        return 1
      fi
      ok "Custom SSL certificates exist"
      ;;
    letsencrypt)
      ok "Let's Encrypt will manage certificates automatically"
      ;;
    selfsign)
      ok "Self-signed certificates will be generated automatically"
      ;;
    upstream)
      ok "Upstream proxy handles SSL"
      ;;
  esac

  return 0
}

# ============================================================================
# Main diagnostics
# ============================================================================

log ""
log "${BOLD}ODK Central Configuration Doctor${RESET}"
log ""

section "📋 Prerequisites"
check_docker
check_submodules

section "📄 Configuration Files"
check_env_file
check_s3_config
check_db_config
check_ssl_files

section "🐳 Docker Environment"
check_networks
check_port_conflicts

section "🏃 Runtime Status"
check_containers
check_db_connectivity
check_garage_runtime

section "🔒 File Permissions"
check_file_permissions

# ============================================================================
# Summary
# ============================================================================

log ""
section "📊 Diagnostic Summary"

if [ $ERROR_COUNT -eq 0 ] && [ $WARNING_COUNT -eq 0 ]; then
  ok "${BOLD}All checks passed!${RESET} Your ODK Central setup looks healthy."
  exit 0
elif [ $ERROR_COUNT -eq 0 ]; then
  warn "${BOLD}${WARNING_COUNT} warning(s) found${RESET} but no critical errors."
  log "Your setup should work, but review warnings above."
  exit 0
else
  err "${BOLD}${ERROR_COUNT} error(s) and ${WARNING_COUNT} warning(s) found${RESET}"
  log ""
  log "Fix the errors above before starting ODK Central."
  log ""
  log "Common fixes:"
  log "  • Missing .env: Run ./scripts/init-odk.sh"
  log "  • Missing networks: docker network create central_db_net && docker network create central_web"
  log "  • Missing submodules: git submodule update --init --recursive"
  log "  • Garage not configured: ./scripts/add-s3.sh (if using Garage)"
  exit 1
fi
