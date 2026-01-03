#!/bin/bash
# Generate s3.conf from template using environment variables
# Run this after modifying .env to regenerate S3 nginx configuration

set -e

# Load specific environment variables from .env
if [ -f .env ]; then
  # Only load variables we need (avoids issues with dots in EXTRA_SERVER_NAME)
  export DOMAIN=$(grep "^DOMAIN=" .env | cut -d= -f2 | head -1)
  export SSL_TYPE=$(grep "^SSL_TYPE=" .env | cut -d= -f2 | head -1)
  export S3_BUCKET_NAME=$(grep "^S3_BUCKET_NAME=" .env | cut -d= -f2 | head -1)
else
  echo "ERROR: .env file not found"
  exit 1
fi

# Set defaults if not found in .env
DOMAIN=${DOMAIN:-central.local}
SSL_TYPE=${SSL_TYPE:-selfsign}
S3_BUCKET_NAME=${S3_BUCKET_NAME:-odk-central}

# Determine CERT_DOMAIN
if [ "$SSL_TYPE" = "customssl" ]; then
  CERT_DOMAIN="local"
else
  CERT_DOMAIN="$DOMAIN"
fi

# Generate s3.conf using envsubst
# Explicitly list variables to avoid replacing nginx variables like $host
envsubst '${DOMAIN} ${SSL_TYPE} ${CERT_DOMAIN} ${S3_BUCKET_NAME}' \
  < files/nginx/s3.conf.template \
  > files/nginx/s3.conf

echo "✓ Generated files/nginx/s3.conf"
echo "  DOMAIN=$DOMAIN"
echo "  SSL_TYPE=$SSL_TYPE"
echo "  CERT_DOMAIN=$CERT_DOMAIN"
echo "  S3_BUCKET_NAME=$S3_BUCKET_NAME"
echo ""
echo "S3 API endpoint: ${S3_BUCKET_NAME}.s3.${DOMAIN}"
echo "S3 Web UI:       web.${DOMAIN}"
echo ""
echo "Restart nginx to apply:"
echo "  docker compose restart nginx"
