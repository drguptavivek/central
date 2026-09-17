#!/bin/sh
set -eu

log() { echo >&2 "[$(basename "$0")] $*"; }

domain='odk-nginx.example.test'
base_url="https://${domain}:11002"

request_status() {
  method="$1"
  path="$2"
  auth="$3"

  case "$auth" in
    cookie) auth_header='Cookie: __Host-session=fixture' ;;
    bearer) auth_header='Authorization: Bearer fixture' ;;
    basic) auth_header='Authorization: Basic dGVzdDpwYXNzd29yZA==' ;;
    fieldkey|st|none) auth_header='' ;;
    *) log "Unknown auth transport: $auth"; return 2 ;;
  esac

  if [ -n "$auth_header" ]; then
    curl --insecure --globoff --silent --show-error --output /dev/null \
      --write-out '%{http_code}' --resolve "${domain}:11002:127.0.0.1" \
      --request "$method" --header "$auth_header" "${base_url}${path}" || true
  else
    curl --insecure --globoff --silent --show-error --output /dev/null \
      --write-out '%{http_code}' --resolve "${domain}:11002:127.0.0.1" \
      --request "$method" "${base_url}${path}" || true
  fi
}

assert_status() {
  expected="$1"
  method="$2"
  path="$3"
  auth="$4"

  status="$(request_status "$method" "$path" "$auth")"
  if [ "$status" != "$expected" ]; then
    log "Expected ${expected} for ${method} ${path} (${auth}); got ${status}"
    exit 1
  fi
}

assert_rejected() {
  method="$1"
  path="$2"
  auth="$3"
  status="$(request_status "$method" "$path" "$auth")"
  case "$status" in
    403|405) ;;
    *)
      log "Expected rejection for ${method} ${path} (${auth}); got ${status}"
      exit 1
      ;;
  esac
}

log 'Waiting for the production-template WAF fixture...'
attempt=0
status=''
while [ "$attempt" -lt 60 ]; do
  status="$(curl --insecure --globoff --silent --output /dev/null \
    --resolve "${domain}:11002:127.0.0.1" --write-out '%{http_code}' \
    "${base_url}/client-config.json" || true)"
  [ "$status" = 200 ] && break
  attempt=$((attempt + 1))
  sleep 0.25
done
[ "$status" = 200 ] || {
  log "Production-template fixture did not become ready; got ${status}"
  exit 1
}

# Each row is METHOD|PATH|AUTH_TRANSPORT. The raw and percent-encoded forms
# exercise the same OData names after ModSecurity's argument parsing.
while IFS='|' read -r method path auth; do
  [ -z "$method" ] && continue
  assert_status 200 "$method" "$path" "$auth"
done <<'EOF'
GET|/v1/projects/1/forms/simple.svc|cookie
GET|/v1/projects/1/forms/simple.svc/$metadata|bearer
GET|/v1/projects/1/forms/simple.svc/Submissions?$filter=year(__system/submissionDate)%20eq%202026|basic
GET|/v1/projects/1/forms/simple.svc/Submissions?%24filter=year%28__system%2FsubmissionDate%29%20eq%202026&%24select=__id|fieldkey
GET|/v1/projects/1/forms/simple.svc/Submissions('uuid:1234')?%24select=__id|bearer
GET|/v1/projects/1/forms/simple.svc/Submissions.children.child?%24top=1&%24skip=0|st
GET|/v1/projects/1/forms/simple/draft.svc/Submissions?%24count=true|cookie
GET|/v1/projects/1/datasets/tree.svc|bearer
GET|/v1/projects/1/datasets/tree.svc/$metadata|basic
GET|/v1/projects/1/datasets/tree.svc/Entities?%24orderby=label%20desc&viewAs=1|fieldkey
GET|/v1/key/fixture/projects/1/forms/simple.svc/Submissions?%24search=Alice|fieldkey
GET|/v1/projects/1/forms/simple.svc/Submissions?st=fixture&%24filter=startswith%28name%2C%27A%27%29|st
PUT|/v1/projects/1/forms/simple.svc/Submissions|basic
PATCH|/v1/projects/1/forms/simple.svc/Submissions|bearer
DELETE|/v1/projects/1/forms/simple.svc/Submissions|none
EOF

# These controls must remain blocked. They are outside the OData query/path
# exception, use a non-OData attack payload, target a restricted file, or use
# an unsupported method/surface.
assert_status 403 GET '/v1/projects?foo=%27%20OR%201%3D1%20--' none
assert_status 403 GET '/v1/projects?foo=%3Cscript%3Ealert%281%29%3C%2Fscript%3E' none
assert_status 403 GET '/v1/projects/1/forms/simple.svc/Submissions?%24filter=%3Cscript%3Ealert%281%29%3C%2Fscript%3E' none
assert_status 403 GET '/v1/not-odata/example.svc/Submissions?%24filter=year%28x%29%20eq%202026' none
assert_status 403 GET '/v1/.git/config' none
assert_rejected TRACE /v1/projects none
assert_status 403 PUT /projects none

log 'OData route/query/auth matrix and non-OData controls passed.'
