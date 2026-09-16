#!/bin/sh
set -eu

# Jonas has rendered the ODK template at this point. ODK's `upstream` mode
# means that a reverse proxy terminates TLS before forwarding plain HTTP here.
if [ "${ODK_SSL_TYPE}" = upstream ]; then
  odk_conf=/etc/nginx/conf.d/odk.conf
  sed -i \
    -e 's/listen 443 default_server ssl;/listen 80 default_server;/' \
    -e 's/listen 443 ssl;/listen 80;/' \
    -e '/^[[:space:]]*ssl_/d' \
    -e 's/X-Forwarded-Proto \$scheme/X-Forwarded-Proto https/' \
    "${odk_conf}"
  rm -f /etc/nginx/conf.d/redirector.conf
fi
