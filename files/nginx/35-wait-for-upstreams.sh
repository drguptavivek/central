#!/bin/sh
set -eu

# NGINX resolves static upstream names while loading the generated ODK vhost.
# Wait for Compose DNS before Jonas starts NGINX and activates a new certificate,
# otherwise its one-time reload can fail and leave only the base config active.
for odk_upstream in service enketo; do
  attempt=0
  until getent hosts "${odk_upstream}" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "${attempt}" -ge 60 ]; then
      echo "Timed out waiting for Compose DNS name: ${odk_upstream}" >&2
      exit 1
    fi
    sleep 1
  done
done
