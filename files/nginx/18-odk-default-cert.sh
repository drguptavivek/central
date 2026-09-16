#!/bin/sh
set -eu

# Preserve Central's catch-all TLS vhost without reviving setup-odk.sh. This
# certificate is intentionally invalid for every deployment host and is served
# only when a request misses the configured DOMAIN server block.
odk_default_cert_dir=/etc/nginx/ssl
if [ ! -s "${odk_default_cert_dir}/nginx.default.crt" ] ||
   [ ! -s "${odk_default_cert_dir}/nginx.default.key" ]; then
  mkdir -p "${odk_default_cert_dir}"
  openssl req -x509 -nodes -newkey rsa:2048 \
    -subj /CN=invalid.local \
    -keyout "${odk_default_cert_dir}/nginx.default.key" \
    -out "${odk_default_cert_dir}/nginx.default.crt" \
    -days 365000 >/dev/null 2>&1
fi
