#!/bin/sh
set -eu

# NGINX's stock entrypoint sources *.envsh inside a pipeline subshell. Template
# variables survive long enough for envsubst, but runtime exports do not reach
# Jonas's certificate loop. Set only the runtime CA switch here, then delegate
# unchanged startup and signal handling to Jonas.
case "${SSL_TYPE:-letsencrypt}" in
  selfsign)
    export USE_LOCAL_CA=1
    ;;
  letsencrypt)
    export USE_LOCAL_CA="${USE_LOCAL_CA:-0}"
    ;;
  customssl|upstream)
    export USE_LOCAL_CA=0
    ;;
  *)
    echo "SSL_TYPE must be letsencrypt, selfsign, customssl, or upstream" >&2
    exit 1
    ;;
esac

exec /scripts/start_nginx_certbot.sh "$@"
