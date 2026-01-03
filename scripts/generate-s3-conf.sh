#!/bin/bash
# Generate s3.conf from template using environment variables
# Run this after modifying .env to regenerate S3 nginx configuration

set -e

# Load environment variables from .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "ERROR: .env file not found"
  exit 1
fi

# Set defaults
DOMAIN=${DOMAIN:-central.local}
SSL_TYPE=${SSL_TYPE:-selfsign}

# Determine CERT_DOMAIN
if [ "$SSL_TYPE" = "customssl" ]; then
  CERT_DOMAIN="local"
else
  CERT_DOMAIN="$DOMAIN"
fi

# Generate s3.conf using envsub
envsubst \
  < files/nginx/s3.conf.template \
  > files/nginx/s3.conf

echo "✓ Generated files/nginx/s3.conf"
echo "  DOMAIN=$DOMAIN"
echo "  SSL_TYPE=$SSL_TYPE"
echo "  CERT_DOMAIN=$CERT_DOMAIN"
echo ""
echo "Restart nginx to apply:"
echo "  docker compose ... restart nginx"
