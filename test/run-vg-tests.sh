#!/bin/bash
set -e

# This script ensures a clean database environment for VG integration tests.
# It works around the limitations of the upstream 'drop owned by current_user' cleanup
# by completely recreating the test database.

echo ">>> Resetting test database..."
docker compose -f docker-compose.yml -f docker-compose.vg-dev.yml exec -T postgres14 psql -U odk -c "DROP DATABASE IF EXISTS jubilant_test;"
docker compose -f docker-compose.yml -f docker-compose.vg-dev.yml exec -T postgres14 psql -U odk -c "CREATE DATABASE jubilant_test OWNER jubilant;"

echo ">>> Running TOTP integration tests..."
docker compose -f docker-compose.yml -f docker-compose.vg-dev.yml exec -T service sh -lc 'cd /usr/odk && NODE_CONFIG_ENV=test BCRYPT=insecure NODE_OPTIONS=--no-warnings ./node_modules/.bin/mocha --timeout 10000 test/integration/api/vg-web-user-totp.js'