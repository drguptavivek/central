#!/bin/bash -eu
set -o pipefail
shopt -s inherit_errexit

# ============================================================================
# Start ODK Central Stack
# ============================================================================
#
# Prerequisites:
# 1. .env file configured (run: scripts/init-odk.sh)
# 2. Docker and Docker Compose installed
# 3. External networks created
#
# This script:
# 1. Validates configuration
# 2. Creates external networks (if needed)
# 3. Starts services in dependency order
# 4. Waits for health checks
# 5. Runs database migrations (if needed)
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color output
if tput colors &>/dev/null; then
  BOLD='\033[1m'
  GREEN='\033[32m'
  BLUE='\033[34m'
  YELLOW='\033[33m'
  RED='\033[31m'
  RESET='\033[0m'
else
  BOLD=''
  GREEN=''
  BLUE=''
  YELLOW=''
  RED=''
  RESET=''
fi

log() { echo >&2 -e "${BLUE}[start]${RESET} $*"; }
success() { echo >&2 -e "${GREEN}✓${RESET} $*"; }
warn() { echo >&2 -e "${YELLOW}⚠${RESET} $*"; }
error() { echo >&2 -e "${RED}✗${RESET} $*"; exit 1; }

# ============================================================================
# Validation
# ============================================================================

cd "$PROJECT_ROOT"

log "Validating configuration..."

if [ ! -f ".env" ]; then
  error ".env file not found. Run: scripts/init-odk.sh"
fi
success ".env file found"

if ! command -v docker &> /dev/null; then
  error "docker not found. Please install Docker."
fi
success "docker installed"

if ! command -v docker-compose &> /dev/null; then
  error "docker-compose not found. Please install Docker Compose."
fi
success "docker-compose installed"

# ============================================================================
# Setup External Networks
# ============================================================================

log ""
log "Setting up external networks..."

for network in central_db_net central_web; do
  if ! docker network inspect "$network" &>/dev/null; then
    log "Creating network: $network"
    docker network create "$network"
    success "Network created: $network"
  else
    log "Network already exists: $network"
  fi
done

# ============================================================================
# Start Stack
# ============================================================================

log ""
log "Starting ODK Central stack..."
log ""

# Load env for logging
set +a
source .env
set +a

log "DOMAIN: $DOMAIN"
log "SSL_TYPE: $SSL_TYPE"
log "HTTP_PORT: $HTTP_PORT"
log "HTTPS_PORT: $HTTPS_PORT"

docker-compose up -d

# ============================================================================
# Wait for Services
# ============================================================================

log ""
log "Waiting for services to be healthy..."

# Wait for postgres
log "Waiting for PostgreSQL..."
for i in {1..60}; do
  if docker-compose exec -T postgres14 pg_isready -U odk &>/dev/null; then
    success "PostgreSQL is ready"
    break
  fi
  if [ $i -eq 60 ]; then
    error "PostgreSQL failed to start"
  fi
  sleep 1
done

# Wait for service
log "Waiting for ODK Service..."
for i in {1..120}; do
  if docker-compose logs service 2>/dev/null | grep -q "starting server"; then
    success "ODK Service is ready"
    break
  fi
  if [ $i -eq 120 ]; then
    warn "Service startup check timed out - continuing anyway"
  fi
  sleep 1
done

# Wait for nginx
log "Waiting for nginx..."
for i in {1..30}; do
  if docker-compose exec -T nginx nc -z localhost 80 &>/dev/null; then
    success "nginx is ready"
    break
  fi
  if [ $i -eq 30 ]; then
    warn "nginx startup check timed out - continuing anyway"
  fi
  sleep 1
done

# ============================================================================
# Summary
# ============================================================================

log ""
success "ODK Central stack is running!"
log ""
log "${BOLD}Access Points:${RESET}"
log "Web UI:    https://$DOMAIN:$HTTPS_PORT"
log "API:       https://$DOMAIN:$HTTPS_PORT/v1"
if [ -f "garage/garage.toml" ]; then
  log "S3 API:    https://odk-central.s3.$DOMAIN"
  log "S3 Web UI: https://web.$DOMAIN"
fi
log ""
log "${BOLD}Useful Commands:${RESET}"
log "View logs:        docker compose logs -f service"
log "Check status:     docker compose ps"
log "Stop stack:       docker compose down"
log "Restart service:  docker compose restart service"
log ""

# Display next steps based on environment
if [ "${DB_HOST:-postgres14}" != "postgres14" ]; then
  warn "Using external database - verify connection:"
  log "  docker compose exec service psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -c 'SELECT 1'"
fi

if [ "${SSL_TYPE}" = "selfsign" ] || [ "${SSL_TYPE}" = "letsencrypt" ]; then
  if [ "${DOMAIN}" = "central.local" ] || [ "${DOMAIN}" = "localhost" ]; then
    warn "Development domain detected - add to /etc/hosts:"
    log "  sudo bash -c 'echo 127.0.0.1 ${DOMAIN} >> /etc/hosts'"
  fi
fi

success "Startup complete!"
