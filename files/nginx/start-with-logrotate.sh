#!/bin/bash -eu
set -o pipefail
shopt -s inherit_errexit

start_logrotate_loop() {
  echo "starting nginx logrotate loop (interval=86400s)"

  mkdir -p /var/lib/logrotate
  touch /var/lib/logrotate/status

  (
    while true; do
      logrotate -s /var/lib/logrotate/status /etc/logrotate.d/nginx-container || true
      sleep 86400
    done
  ) &
}

start_logrotate_loop
exec /scripts/setup-odk.sh
