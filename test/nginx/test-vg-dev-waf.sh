#!/bin/sh
set -eu

log() { echo >&2 "[$(basename "$0")] $*"; }

domain='odk-nginx.example.test'
baseUrl="https://${domain}:11001"

log 'Waiting for the development nginx fixture...'
attempt=0
status=''
# Match the fixture's 90-second startup grace plus 60 health retries.
while [ "$attempt" -lt 600 ]; do
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
versionResponse="$(curl --insecure --silent --show-error --write-out '\n%{http_code}' \
  --resolve "${domain}:11001:127.0.0.1" "${baseUrl}/version.txt")"
versionStatus="$(printf '%s\n' "$versionResponse" | tail -n 1)"
versionBody="$(printf '%s\n' "$versionResponse" | sed '$d')"
apiStatus="$(curl --insecure --silent --output /dev/null \
  --resolve "${domain}:11001:127.0.0.1" --write-out '%{http_code}' \
  "${baseUrl}/v1/@id/__x00__plugin-vue:export-helper")"

[ "$viteStatus" = 200 ] || {
  log "Expected Vite virtual module status 200; got $viteStatus"
  exit 1
}
[ "$versionStatus" = 200 ] || {
  log "Expected nginx-served version.txt status 200; got $versionStatus"
  exit 1
}
for repository in central client server; do
  case "$repository" in
    central) sha="$(git -C ../.. rev-parse HEAD)" ;;
    *) sha="$(git -C "../../$repository" rev-parse HEAD)" ;;
  esac
  printf '%s\n' "$versionBody" | grep -Fq "$sha" || {
    log "Expected version.txt to contain checked-out $repository SHA $sha"
    exit 1
  }
done
[ "$apiStatus" = 403 ] || {
  log "Expected API WAF probe status 403; got $apiStatus"
  exit 1
}

log 'Nginx version metadata, Vite bypass, and API WAF boundary passed.'
