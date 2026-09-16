#!/bin/sh
set -eu

# The WAF image pins CRS but intentionally ships only the setup example so
# consumers can provide policy. Use the pinned release's defaults when Central
# does not mount an explicit setup file.
if [ ! -e /etc/modsecurity/crs/crs-setup.conf ]; then
  cp /etc/modsecurity/crs/crs-setup.conf.example /etc/modsecurity/crs/crs-setup.conf
fi

case "${OIDC_ENABLED:-false}" in
  true|false) oidc_enabled="${OIDC_ENABLED:-false}" ;;
  *) echo "OIDC_ENABLED must be true or false" >&2; exit 1 ;;
esac

cat > /usr/share/nginx/html/client-config.json <<EOF
{
  "oidcEnabled": ${oidc_enabled},
  "sentryDsn": "${SENTRY_DSN_FRONTEND:-}"
}
EOF
