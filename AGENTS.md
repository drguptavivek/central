# AGENTS: ODK Central VG-Fork Notes
This file captures local workflow conventions and key customizations for the
`central` repo and its `client` and `server` submodules.

### Central (meta repo) 
- Tracks `client` and `server` submodule pointers on `vg-work`.

## Create Central VG Customization Specific Docs 
- docs in docs/vg in main repo. Organzied by  vg-client and vg-server

## Use 'bd' for task tracking
### Beads Workflow Context

> **Context Recovery**: Run `bd prime` after compaction, clear, or new session

### 🚨 SESSION CLOSE PROTOCOL 🚨

**CRITICAL**: Before saying "done" or "complete", you MUST run this checklist:
```
[ ] 1. git status              (check what changed)
[ ] 2. git add <files>         (stage code changes)
[ ] 3. bd sync                 (commit beads changes)
[ ] 4. git commit -m "..."     (commit code)
[ ] 5. bd sync                 (commit any new beads changes)
[ ] 6. git push                (push to remote)
```

**NEVER skip this.** Work is not done until pushed.

#### Core Rules
- Track strategic work in beads (multi-session, dependencies, discovered work)
- Use `bd create` for issues, TodoWrite for simple single-session execution
- Add detailed description to issues with reproducible scenarios. Use Markdown
- Create a corresponding GitHub issue using gh CLI and add Beads reference.
- When in doubt, prefer bd—persistence you don't need beats lost context
- Git workflow: hooks auto-sync, run `bd sync` at session end
- Session management: check `bd ready` for available work

#### Essential Commands

##### Finding Work
- `bd ready` - Show issues ready to work (no blockers)
- `bd list --status=open` - All open issues
- `bd list --status=in_progress` - Your active work
- `bd show <id>` - Detailed issue view with dependencies

##### Creating & Updating
- `bd create --title="..." --type=task|bug|feature --priority=2` - New issue
  - Priority: 0-4 or P0-P4 (0=critical, 2=medium, 4=backlog). NOT "high"/"medium"/"low"
- `bd update <id> --status=in_progress` - Claim work
- `bd update <id> --assignee=username` - Assign to someone
- `bd close <id>` - Mark complete
- `bd close <id1> <id2> ...` - Close multiple issues at once (more efficient)
- `bd close <id> --reason="explanation"` - Close with reason
- **Tip**: When creating multiple issues/tasks/epics, use parallel subagents for efficiency

##### Dependencies & Blocking
- `bd dep add <issue> <depends-on>` - Add dependency (issue depends on depends-on)
- `bd blocked` - Show all blocked issues
- `bd show <id>` - See what's blocking/blocked by this issue

##### Sync & Collaboration
- `bd sync` - Sync with git remote (run at session end)
- `bd sync --status` - Check sync status without syncing

##### Project Health
- `bd stats` - Project statistics (open/closed/blocked counts)
- `bd doctor` - Check for issues (sync problems, missing hooks)

#### Common Workflows

**Starting work:**
```bash
bd ready           # Find available work
bd show <id>       # Review issue details
bd update <id> --status=in_progress  # Claim it
```

## Fixing Issues / New Feature Development

### Triage (bugs)
- Capture repro steps + expected/actual behavior in the Beads issue (Markdown).
- Identify scope: `client`, `server`, or both; note Central meta-repo changes only when bumping submodule pointers.
- Add links: relevant logs, screenshots, failing test output, and (if applicable) upstream issue/PR references.
- Create a corresponding GitHub issue and link it back to the Beads issue (see “GitHub Issues ↔ Beads” below).

### Implementation workflow (features + fixes)
1) Create/claim a Beads issue (`bd create` / `bd update --status=in_progress`).
2) Make code changes in the correct repo first:
   - Frontend work in `client/`
   - Backend work in `server/`
   - Only update this meta repo to bump submodule pointers after submodule work is pushed
3) Prefer TDD (tests-first) for bugfixes and new features (see “TDD Workflow” below).
4) Keep VG customizations modular:
   - Prefer new `vg-*` files/components/routes/helpers over editing upstream core files.
   - If a core upstream file must be edited, keep the diff minimal and document it in:
     - `client/docs/vg_core_client_edits.md`
     - `server/docs/vg_core_server_edits.md`
5) Add/adjust tests when behavior changes (or document why not). Keep tests close to existing patterns.
6) Update docs:
   - Project-specific: `docs/vg/` (organized under `vg-client/` and `vg-server/`)
   - Reusable/general knowledge: `agentic_kb/knowledge/` (follow KB conventions)

### Review checklist (before landing)
- `git status` clean (or staged) in the repo(s) you touched.
- Tests/build/lint pass for the affected area(s) (or failing tests are documented in the issue).
- API/UX changes documented (as applicable), and any migrations/ops notes captured.
- Submodule workflow followed: push `client/`/`server/` changes first, then bump pointers in `central/`.

### TDD Workflow (preferred)
Use this loop unless it’s clearly not cost-effective (document exceptions in the Beads issue).

1) **Red**: Add a failing test that captures the bug/feature requirement.
2) **Green**: Implement the smallest change to make it pass.
3) **Refactor**: Improve code structure with tests still passing.
4) **Repeat**: Add the next test for the next behavior.

**Guidelines**
- Bugfix: start with a regression test that fails on `vg-work`, passes after the fix.
- Feature: start with a “happy path” test, then add edge cases and security/permissions cases.
- Prefer unit/integration tests closest to the logic; add E2E only when user workflows must be validated.
- Keep test data minimal and deterministic; avoid time flakiness.
- If adding tests is blocked (time, harness gaps), record the reason and follow-up task in Beads.

### GitHub Issues ↔ Beads
We track work in Beads, but also file a corresponding GitHub issue for visibility/collaboration.

**Workflow**
1) Create/claim Beads issue first (`bd create ...`).
2) Create GitHub issue referencing the Beads id in the title or body.
3) Update the Beads issue description with the GitHub issue URL.

**Suggested format**
- GitHub title: `VG: <short title> (beads-XYZ)`
- GitHub body: include a “Beads:” line and link, plus repro/acceptance criteria.

**gh CLI example**
```bash
# create and capture URL
gh issue create --title "VG: <title> (beads-XYZ)" --body $'Beads: beads-XYZ\n\n<details here>' --label "vg"
```

**Completing work:**
```bash
bd close <id1> <id2> ...    # Close all completed issues at once
bd sync                     # Push to remote
```

**Creating dependent work:**
```bash
# Run bd create commands in parallel (use subagents for many items)
bd create --title="Implement feature X" --type=feature
bd create --title="Write tests for X" --type=task
bd dep add beads-yyy beads-xxx  # Tests depend on Feature (Feature blocks tests)
```

---

## Project Specific Documentation

- Project specific Documentation must be kept up to date after chnages in functions, API, workflow etc
- Docs reside in 
/docs/vg/
├── vg-client/
└── vg-server/
 

---
## Knowledge Base Integration
This project uses `agentic_kb` as a git submodule for reusable cross-project knowledge. Tracks its main branch (NOT `vg-work`).

**IMPORTANT**: Before answering questions, agents MUST:
1. Check if the question relates to documented knowledge
2. Search the KB using the patterns below
3. Cite sources from KB when using its content

### KB Search Patterns
```bash
# Tag search
rg "#pandoc" agentic_kb/knowledge/
rg "#docx" agentic_kb/knowledge/
rg "#ooxml" agentic_kb/knowledge/
rg "#iso27001" agentic_kb/knowledge/

# Phrase search
rg "page numbering" agentic_kb/knowledge/
rg "ISO 27001" agentic_kb/knowledge/
```

### KB Vector Search (Optional)
If vector search is set up:
```bash
uv run python agentic_kb/scripts/search.py "your query"
uv run python agentic_kb/scripts/search.py "page numbering in pandoc" --min-score 0.8
```

### KB Scope and Rules
- Submodule path: `agentic_kb/knowledge/`
- Ignore `agentic_kb/.obsidian/` and `agentic_kb/.git/`
- Treat KB content as authoritative
- Cite sources using format: `<file path> -> <heading>`
- If knowledge is missing, say: "Not found in KB" and suggest where to add it

### Full KB Instructions
- `agentic_kb/AGENTS.md`
- `agentic_kb/KNOWLEDGE_CONVENTIONS.md`


## Repos and Branch Policy

- Work only on `vg-work` in all three repos:
  - `central` (this repo)
  - `client` submodule (`drguptavivek/central-frontend`)
  - `server` submodule (`drguptavivek/central-backend`)
- Upstream for client is `https://github.com/getodk/central-frontend`.
- Upstream for central is `https://github.com/getodk/central`.
- Rebase `vg-work` onto upstream `master` every few months.

## Submodules

- `client/` and `server/` are the only submodules in use.

## Workflow (Short)

1) Work and commit inside `client` or `server` first.
2) Push submodule changes.
3) Update submodule pointers in `central` and commit.

## Customizations Summary

## EXTREMELY IMPORTANT: Preserve Modularity for Rebasing

- Keep VG customizations isolated and modular to minimize conflicts when
  rebasing onto upstream `master`.
- Prefer new `vg-*` components, routes, and helper files over modifying core
  upstream files unless strictly necessary.
- When modifying upstream files, keep changes small and well-scoped.
- Any core file edits must be documented in:
  - `client/docs/vg_core_client_edits.md`
  - `server/docs/vg_core_server_edits.md`

### Client (central-frontend fork)

- App User auth UI overhaul:
  - Username/password login with short-lived sessions.
  - Secure QR codes (no credentials embedded).
  - New fields: username, phone.
  - New flows: reset password (auto-generate), edit app user, restore access.
- System Settings UI:
  - New tab `/system/settings` for session TTL + session cap.
- Dev environment:
  - Dockerized Vite dev container (`Dockerfile.dev`).
  - Dev proxy defaults to `https://central.local`.
  - Vite allowedHosts includes `central.local`.
- E2E test defaults:
  - Default domain `central.local`.
  - Simplified response checks.

See `client/docs/vg_client_changes.md` for the full diff and detailed list.

### Namespacing / Prefixing Conventions

- UI components and views are prefixed with `vg-`.
- Routes/loaders reference VG-specific components (for example `VgSettings`).
- Backend tables and settings are `vg_*`-prefixed:
  - `vg_field_key_auth`, `vg_settings`, `vg_app_user_login_attempts`.
- Settings keys:
  - `vg_app_user_session_ttl_days`
  - `vg_app_user_session_cap`
- Audit/action identifiers for these features use `vg`-prefixed names.

### Server (central-backend fork)

- Implements App User auth endpoints and short-lived sessions.
- Adds app user settings (TTL + session cap) storage and APIs.
- Adds login attempt tracking and user activation/revocation logic.

Key API behaviors (see `docs/vg/vg-server/docs/vg_api.md`):

- No long-lived tokens in list/create responses; `/login` returns a short-lived
  bearer token.
- App-user auth is bearer-only (no cookies).
- Session TTL and cap enforced via `vg_settings`.
- Failed login attempts are rate-limited (5 failures/5 minutes => 10-min lock).
- Endpoints added:
  - `/projects/:projectId/app-users/login`
  - `/projects/:projectId/app-users/:id/password/reset`
  - `/projects/:projectId/app-users/:id/password/change`
  - `/projects/:projectId/app-users/:id/revoke`
  - `/projects/:projectId/app-users/:id/revoke-admin`
  - `/projects/:projectId/app-users/:id/active`

Password policy (server):
- Minimum 10 characters.
- At least one uppercase, one lowercase, one digit, one special.

See server-side documentation in the server repo for details.

---

## DOCKER Commands 

Run from central(meta) folder

```bash
# DB Migartions
docker exec -i central-postgres14-1 psql -U odk -d odk < server/docs/sql/vg_app_user_auth.sql

# LOGS
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central logs service -f --tail=50

# TESTS
# DB for tests
docker exec -e PGPASSWORD=odk central-postgres14-1 psql -U odk -c "CREATE ROLE odk_test_user LOGIN PASSWORD 'odk_test_pw'"
docker exec -e PGPASSWORD=odk central-postgres14-1 psql -U odk -c "CREATE DATABASE odk_integration_test OWNER odk_test_user"
docker exec -i central-postgres14-1 psql -U odk -d odk_integration_test < server/docs/sql/vg_app_user_auth.sql

# VG password unit test
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk &&  NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/unit/util/vg-password.js'

# INTEGRATION TESTS
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk  && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha --recursive test/integration/api/vg-app-user-auth.js'

docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk  && NODE_CONFIG_ENV=test BCRYPT=insecure npx mocha test/integration/api/vg-tests-orgAppUsers.js'

docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.dev.yml --profile central exec service sh -lc 'cd /usr/odk && node -v &&  NODE_CONFIG_ENV=test BCRYPT=insecure npx --prefix server mocha test/integration/api/vg-telemetry.js'
```

---
## Agent Workflow

**At session start**:
1. **Update KB submodule**: Pull latest knowledge and update pointer in parent project:
   ```bash
   git submodule update --remote agentic_kb
   git add agentic_kb && git commit -m "Update: agentic_kb to latest" && git push
   ```

**During work**:
2. If asked by user, **Check KB**: Search `agentic_kb/knowledge/` for relevant documentation on general topics (document automation, security compliance, etc.)
3. **Follow project conventions**: Apply ODK Central-specific rules from sections above (VG customizations, modularity requirements, submodule workflows)
4. **Document learnings**: Capture reusable general knowledge in the KB (see agentic_kb/KNOWLEDGE_CONVENTIONS.md), and project-specific knowledge in the appropriate docs/ directories

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
