#!/bin/sh
set -eu

log() { echo >&2 "[$(basename "$0")] $*"; }

domain='odk-nginx.example.test'
baseUrl="https://${domain}:11001"

log 'Waiting for the development nginx fixture...'
attempt=0
status=''
while [ "$attempt" -lt 60 ]; do
  status="$(curl --insecure --silent --output /dev/null \
    --resolve "${domain}:11001:127.0.0.1" --write-out '%{http_code}' \
    "${baseUrl}/client-config.json" || true)"
  [ "$status" = 200 ] && break
  attempt=$((attempt + 1))
  sleep 0.25
done
[ "$status" = 200 ]

viteStatus="$(curl --insecure --silent --output /dev/null \
  --resolve "${domain}:11001:127.0.0.1" --write-out '%{http_code}' \
  "${baseUrl}/@id/__x00__plugin-vue:export-helper")"
apiStatus="$(curl --insecure --silent --output /dev/null \
  --resolve "${domain}:11001:127.0.0.1" --write-out '%{http_code}' \
  "${baseUrl}/v1/@id/__x00__plugin-vue:export-helper")"

[ "$viteStatus" = 200 ] || {
  log "Expected Vite virtual module status 200; got $viteStatus"
  exit 1
}
[ "$apiStatus" = 403 ] || {
  log "Expected API WAF probe status 403; got $apiStatus"
  exit 1
}

log 'Vite bypass and API WAF boundary passed.'
