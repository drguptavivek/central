# v2026.3.0-vg.2

Corrective release for the v2026.3.0 fork integration.

- Restores `docker-compose.yml` and the upstream image/configuration files to exact upstream v2026.3.0 versions, including frontend v2026.3.0, Redis 8.10.1, Enketo 7.6.4, PostgreSQL 14.24, and Node 24.20.0.
- Retains the VG WAF runtime layer in `nginx.dockerfile` while using the upstream Node build-stage version.
- Prefixes the fork-owned Custom Properties Vue components with `vg-` and removes an unused duplicate XForms source file.
- Reconciles the Central, client, and server core-edit ledgers with the exact v2026.3.0 tag-relative diffs.
- Documents the historical unprefixed submission-event migration phase as a frozen compatibility exception; it is not renamed because deployed databases may already record it.

Validation: Compose environment parity, merged Compose rendering, client ESLint, XForms TypeScript check, and production frontend build pass. The focused local Karma launch was blocked by the host Chrome/EMFILE condition; GitHub Actions is the browser-test authority for this corrective release.
