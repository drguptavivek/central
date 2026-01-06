#!/bin/bash -eu
set -o pipefail
shopt -s inherit_errexit

# ============================================================================
# ODK Central VG Fork - Interactive Initialization Script
# ============================================================================
#
# This script guides you through 4 key decisions and auto-configures everything:
# 1. Environment Type: Dev | Prod
# 2. S3 Storage: None (PostgreSQL) | Local (Garage) | External Provider
# 3. PostgreSQL Instance: Container | Local PostgreSQL | Hosted Service
# 4. SSL Termination: selfsign | letsencrypt | customssl | upstream
#
# Then generates .env with all derived configuration.
# ============================================================================

set +e
tput colors &>/dev/null
HAS_COLOR=$?
set -e

if [ $HAS_COLOR -eq 0 ]; then
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

log() { echo >&2 -e "${BLUE}[init]${RESET} $*"; }
success() { echo >&2 -e "${GREEN}✓${RESET} $*"; }
warn() { echo >&2 -e "${YELLOW}⚠${RESET} $*"; }
error() { echo >&2 -e "${RED}✗${RESET} $*"; exit 1; }

# ============================================================================
# Helper Functions
# ============================================================================

prompt_choice() {
  local prompt_text="$1"
  shift
  local options=("$@")
  local choice

  echo >&2 ""
  echo >&2 -e "${BOLD}${prompt_text}${RESET}"
  for i in "${!options[@]}"; do
    echo >&2 "  $((i+1))) ${options[$i]}"
  done
  echo >&2 -n "Select (1-${#options[@]}): "
  read -r choice

  # Validate input
  if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt ${#options[@]} ]; then
    error "Invalid selection. Please enter a number between 1 and ${#options[@]}"
  fi

  echo "${options[$((choice-1))]}"
}

prompt_text() {
  local prompt_text="$1"
  local default="${2:-}"
  local input

  echo >&2 ""
  if [ -n "$default" ]; then
    echo >&2 -n -e "${BOLD}${prompt_text}${RESET} [${default}]: "
  else
    echo >&2 -n -e "${BOLD}${prompt_text}${RESET}: "
  fi
  read -r input

  if [ -z "$input" ]; then
    echo "$default"
  else
    echo "$input"
  fi
}

# ============================================================================
# Main Flow
# ============================================================================

log "Starting ODK Central initialization..."
log ""
log "This script will ask 4 key questions, then auto-generate .env configuration."

# Decision 1: Environment Type
ENV_TYPE=$(prompt_choice "1. Environment Type:" "Dev (development, localhost)" "Prod (production, public domain)")
log "Environment: $ENV_TYPE"

# Decision 2: S3 Storage
S3_CHOICE=$(prompt_choice "2. S3 Blob Storage:" "None (store blobs in PostgreSQL)" "Local Garage S3" "External S3 (AWS, MinIO, etc.)")
log "S3 Storage: $S3_CHOICE"

# Decision 3: PostgreSQL
DB_CHOICE=$(prompt_choice "3. PostgreSQL Instance:" "Container (postgres14 in docker-compose)" "Local PostgreSQL (on host machine)" "Hosted Service (AWS RDS, Google Cloud SQL, etc.)")
log "Database: $DB_CHOICE"

# Decision 4: SSL
SSL_CHOICE=$(prompt_choice "4. SSL Termination:" "selfsign (self-signed, dev only)" "letsencrypt (automated HTTPS)" "customssl (your own certificates)" "upstream (behind reverse proxy)")
log "SSL: $SSL_CHOICE"

# Decision 5: Domain
log ""
if [[ "$ENV_TYPE" == "Dev"* ]]; then
  DEFAULT_DOMAIN="central.local"
else
  DEFAULT_DOMAIN="your.domain.com"
fi

DOMAIN=$(prompt_text "Domain name" "$DEFAULT_DOMAIN")
log "Domain: $DOMAIN"

# For prod, get sysadmin email
if [[ "$ENV_TYPE" == "Prod"* ]]; then
  SYSADMIN_EMAIL=$(prompt_text "System Administrator Email" "admin@${DOMAIN}")
else
  SYSADMIN_EMAIL="admin@${DOMAIN}"
fi
log "Sysadmin Email: $SYSADMIN_EMAIL"

# ============================================================================
# Auto-Derive Configuration
# ============================================================================

log ""
log "Deriving configuration from decisions..."

# SSL: Derive ports
if [[ "$SSL_CHOICE" == "upstream"* ]]; then
  HTTP_PORT=8080
  HTTPS_PORT=8443
else
  HTTP_PORT=80
  HTTPS_PORT=443
fi

# SSL: Derive type string
case "$SSL_CHOICE" in
  "selfsign"*)     SSL_TYPE=selfsign ;;
  "letsencrypt"*)  SSL_TYPE=letsencrypt ;;
  "customssl"*)    SSL_TYPE=customssl ;;
  "upstream"*)     SSL_TYPE=upstream ;;
esac

# S3: Derive server, credentials, bucket
S3_SERVER=""
S3_BUCKET_NAME="odk-central"
S3_ACCESS_KEY=""
S3_SECRET_KEY=""
GENERATE_S3_CREDS=false
EXTRA_SERVER_NAME=""

case "$S3_CHOICE" in
  "None"*)
    S3_SERVER=""
    log "S3 disabled → blobs will be stored in PostgreSQL"
    ;;
  "Local Garage"*)
    S3_SERVER="https://${S3_BUCKET_NAME}.s3.${DOMAIN}"
    GENERATE_S3_CREDS=true
    # For Let's Encrypt with Garage, need S3 subdomains in cert
    if [[ "$SSL_CHOICE" == "letsencrypt"* ]]; then
      EXTRA_SERVER_NAME="${S3_BUCKET_NAME}.s3.${DOMAIN} web.${DOMAIN}"
    fi
    log "S3 enabled (Garage) → S3_SERVER=${S3_SERVER}"
    ;;
  "External S3"*)
    read -r S3_SERVER < <(prompt_text "S3 Server URL" "https://mybucket.s3.amazonaws.com")
    S3_BUCKET_NAME=$(prompt_text "S3 Bucket Name" "mybucket")
    S3_ACCESS_KEY=$(prompt_text "S3 Access Key" "")
    S3_SECRET_KEY=$(prompt_text "S3 Secret Key" "")
    log "S3 enabled (External) → S3_SERVER=${S3_SERVER}"
    ;;
esac

# Database: Derive host, user, password
DB_HOST="postgres14"
DB_USER="odk"
DB_PASSWORD="odk"
DB_NAME="odk"
DB_SSL="null"

case "$DB_CHOICE" in
  "Container"*)
    log "Database: postgres14 container (default)"
    ;;
  "Local PostgreSQL"*)
    DB_HOST=$(prompt_text "PostgreSQL Host" "localhost")
    DB_USER=$(prompt_text "PostgreSQL User" "odk")
    DB_PASSWORD=$(prompt_text "PostgreSQL Password" "odk")
    DB_NAME=$(prompt_text "Database Name" "odk")
    DB_SSL=$(prompt_text "Use SSL connection? (null/true)" "null")
    log "Database: local PostgreSQL at ${DB_HOST}"
    ;;
  "Hosted Service"*)
    DB_HOST=$(prompt_text "Database Host (RDS endpoint, etc.)" "")
    DB_USER=$(prompt_text "Database User" "odk")
    DB_PASSWORD=$(prompt_text "Database Password" "")
    DB_NAME=$(prompt_text "Database Name" "odk")
    DB_SSL="true"  # Always true for managed services
    log "Database: hosted service at ${DB_HOST}"
    ;;
esac

# ============================================================================
# Generate .env File
# ============================================================================

log ""
log "Generating .env file..."

ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
  warn "Backing up existing .env to .env.backup"
  cp "$ENV_FILE" "$ENV_FILE.backup"
fi

cat > "$ENV_FILE" <<EOF
# ============================================================================
# ODK Central Configuration
# Generated by: scripts/init-odk.sh on $(date)
# ============================================================================

# Decision 1: Environment Type
# Selected: $ENV_TYPE

# Decision 2: S3 Storage
# Selected: $S3_CHOICE

# Decision 3: PostgreSQL Instance
# Selected: $DB_CHOICE

# Decision 4: SSL Termination
# Selected: $SSL_CHOICE

# ============================================================================
# 1. DOMAIN AND SSL
# ============================================================================

DOMAIN=${DOMAIN}
SYSADMIN_EMAIL=${SYSADMIN_EMAIL}
SSL_TYPE=${SSL_TYPE}
HTTP_PORT=${HTTP_PORT}
HTTPS_PORT=${HTTPS_PORT}
EOF

if [ -n "$EXTRA_SERVER_NAME" ]; then
  echo "EXTRA_SERVER_NAME=${EXTRA_SERVER_NAME}" >> "$ENV_FILE"
fi

cat >> "$ENV_FILE" <<EOF

# ============================================================================
# 2. DATABASE
# ============================================================================

DB_HOST=${DB_HOST}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME}
DB_SSL=${DB_SSL}

# ============================================================================
# 3. S3 BLOB STORAGE
# ============================================================================

EOF

if [ -n "$S3_SERVER" ]; then
  cat >> "$ENV_FILE" <<EOF
S3_SERVER=${S3_SERVER}
S3_BUCKET_NAME=${S3_BUCKET_NAME}
S3_ACCESS_KEY=${S3_ACCESS_KEY}
S3_SECRET_KEY=${S3_SECRET_KEY}
EOF
else
  cat >> "$ENV_FILE" <<EOF
# S3 disabled - blobs stored in PostgreSQL
# To enable, uncomment and configure:
# S3_SERVER=
# S3_BUCKET_NAME=
# S3_ACCESS_KEY=
# S3_SECRET_KEY=
EOF
fi

cat >> "$ENV_FILE" <<EOF

# ============================================================================
# 4. OTHER SETTINGS
# ============================================================================

# Optional: SESSION_LIFETIME=86400  (24 hours, in seconds)
# Optional: SERVICE_NODE_OPTIONS=
# Optional: SENTRY_* configuration
# Optional: OIDC_* configuration
# Optional: EMAIL_* configuration

# ============================================================================
# VG FORK SPECIFIC
# ============================================================================

# Nginx base image (includes ModSecurity WAF)
NGINX_BASE_IMAGE=drguptavivek/central-nginx-vg-base:6.0.1
EOF

success ".env file created"

# ============================================================================
# Setup Garage (if selected)
# ============================================================================

if [ "$GENERATE_S3_CREDS" = true ]; then
  log ""
  log "Setting up Garage S3..."

  if command -v uv &> /dev/null; then
    if [ ! -f "garage/garage.toml" ]; then
      log "Running garage/setup-garage.py..."
      uv run --with pyyaml --with questionary python garage/setup-garage.py
      success "Garage configured"
    else
      log "Garage already configured (garage/garage.toml exists)"
    fi
  else
    warn "uv not found - skipping Garage setup"
    warn "Run manually: uv run --with pyyaml --with questionary python garage/setup-garage.py"
  fi
fi

# ============================================================================
# Summary and Next Steps
# ============================================================================

log ""
log "${BOLD}Configuration Summary${RESET}"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Environment:        $ENV_TYPE"
log "Domain:             $DOMAIN"
log "SSL:                $SSL_CHOICE (ports $HTTP_PORT/$HTTPS_PORT)"
log "Database:           $DB_CHOICE"
log "S3 Storage:         $S3_CHOICE"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""
log "${BOLD}Next Steps:${RESET}"
log "1. Review .env file: cat .env"
log "2. Create external networks (if not exists):"
log "   docker network create central_db_net || true"
log "   docker network create central_web || true"
log "3. Start the stack:"
log "   docker compose up -d"
log "4. Check logs:"
log "   docker compose logs -f service"
log ""

if [ "$DB_CHOICE" == *"Hosted"* ]; then
  warn "For hosted database, ensure connection works before starting:"
  warn "  docker compose exec service psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c 'SELECT 1'"
fi

if [[ "$ENV_TYPE" == "Dev"* ]] && [[ "$DOMAIN" == "central.local" ]]; then
  warn "Development setup with central.local - add to /etc/hosts:"
  warn "  127.0.0.1 central.local"
  if [ "$S3_CHOICE" != "None"* ]; then
    warn "  127.0.0.1 odk-central.s3.central.local"
    warn "  127.0.0.1 web.central.local"
  fi
fi

success "Initialization complete!"
