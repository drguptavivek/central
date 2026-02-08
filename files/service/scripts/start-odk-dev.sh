#!/bin/bash -eu
set -o pipefail
shopt -s inherit_errexit

echo "generating local service configuration.."

# Pass these specifically as they are generated at runtime
ENKETO_API_KEY=$(cat /etc/secrets/enketo-api-key) \
BASE_URL=$( [ "${HTTPS_PORT}" = 443 ] && echo https://"${DOMAIN}" || echo https://"${DOMAIN}":"${HTTPS_PORT}" ) \
/scripts/envsub.awk \
    < /usr/share/odk/config.json.template \
    > /usr/odk/config/local.json

SENTRY_RELEASE="$(cat sentry-versions/server)"
export SENTRY_RELEASE
# shellcheck disable=SC2089
SENTRY_TAGS="{ \"version.central\": \"$(cat sentry-versions/central)\", \"version.client\": \"$(cat sentry-versions/client)\" }"
# shellcheck disable=SC2090
export SENTRY_TAGS

echo "running migrations.."
node ./lib/bin/run-migrations

# Logs based on SENTRY_RELEASE and SENTRY_TAGS env variables
echo "logging server upgrade.."
node ./lib/bin/log-upgrade

echo "starting cron.."
cron -f &

# Dev mode: skip memory calculation and just run node --watch
echo "starting server in DEV mode (watch)..."
export WORKER_COUNT=1

# Watch lib and config directories
exec node --watch --watch-path=./lib --watch-path=./config ./lib/bin/run-server.js