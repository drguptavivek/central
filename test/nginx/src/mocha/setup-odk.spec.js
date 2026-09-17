const { execSync } = require('node:child_process');

const { assert } = require('../lib');
const request = require('./request');

const log = (...args) => console.log('[setup-odk.spec]', ...args);
const service = 'nginx-test-setup-odk';

describe('setup-odk.sh', function() {
  describe('SENTRY_DSN_FRONTEND', () => {
    afterEach(() => {
      log('--- CONTAINER LOGS ---');
      dockerCompose({}, `logs --timestamps ${service}`);
      log('--- END CONTAINER LOGS ---');
    });
    after(function() {
      this.timeout(10_000);
      dockerCompose({}, `rm --stop --force ${service}`);
    });

    [
      [ undefined, 'https://o-fake-dsn.ingest.sentry.io' ],
      [
        'https://abcdef0123456789abcdef0123456789@some-dsn.ingest.sentry.io/1234567890123456',
        'https://some-dsn.ingest.sentry.io',
      ],
      [ '', '' ],
      [ 'bad-format', '' ],
      [ 'https://abcdef0123456789abcdef0123456789@some-dsn.ingest.sentry.io/', '' ],
    ].forEach(([ SENTRY_DSN_FRONTEND, expectedCspEntry ]) => {
      it(`should generated expected CSP for SENTRY_DSN_FRONTEND='${SENTRY_DSN_FRONTEND}'`, withNginx({
        SENTRY_DSN_FRONTEND,
      }, async () => {
        // when
        const res = await request(`https://localhost:10003`);

        // then
        assert.equal(res.status, 200);
        assert.equal(
          res.headers.get('Content-Security-Policy'),
          [
            `default-src 'report-sample' 'none'`,
            `connect-src 'self' ${expectedCspEntry} https://translate.google.com https://translate.googleapis.com`,
            `font-src 'self'`,
            `form-action 'self'`,
            `frame-ancestors 'none'`,
            `frame-src 'self' https://getodk.github.io/central/`,
            `img-src data: https:`,
            `manifest-src 'self'`,
            `media-src 'none'`,
            `object-src 'none'`,
            `script-src 'report-sample' 'self'`,
            `style-src 'report-sample' 'self'`,
            `style-src-attr 'unsafe-inline'`,
            `worker-src 'report-sample' blob:`,
            `report-uri /csp-report`,
          ].join('; '),
        );
      }));
    });
  });
});

function dockerCompose(opts, ...args) {
  return execSync(
    `docker compose --file ./nginx/nginx.test.docker-compose.yml ${args.join(' ')}`,
    { stdio:'inherit', ...opts },
  );
}

function withNginx(env, fn) {
  return async function() {
    this.timeout(70_000);

    dockerCompose({ env }, `up --no-deps --build --force-recreate --detach ${service}`);

    const deadline = Date.now() + 60_000;
    let lastError;
    while (true) {
      try {
        const response = await request('https://localhost:10003');
        if (response.status === 200) break;
        lastError = new Error(`Unexpected readiness status ${response.status}.`);
      } catch (error) {
        lastError = error;
      }
      if (Date.now() >= deadline)
        throw new Error(`${service} did not become ready within 60 seconds.`, { cause:lastError });
      await new Promise(resolve => { setTimeout(resolve, 250); });
    }

    await fn();
  };
}
