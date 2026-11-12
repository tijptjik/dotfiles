# Development resource policy

New Zed launches (autostart, desktop entries, `zed` and `zed-preview`) use
UWSM application scopes in `app-development.slice`. Editor and agent children
therefore cannot fail Hyprland's service through its OOMPolicy. Existing editors
must be closed normally and reopened to enter the new scope. Direct application
binary launches bypass the launcher.

The development slice has MemoryHigh=50%, MemoryMax=60% of physical RAM and
2 GiB maximum swap. Each editor scope has 30%/40% thresholds and 1 GiB swap.
The memory limit is a final guard: an oversized job can be killed. Save work.

Zed's Node runtime uses `zed-node`, which places each Node language server
(including TypeScript and its child tsserver processes, Svelte and Tailwind)
in a separate development scope with 15%/20% memory thresholds and 1 GiB swap.
It preserves stdio, arguments, environment and working directory. Node probes
also use this launcher; npm is resolved separately from PATH. Restart Zed
normally after installing the setting; existing servers keep their old scopes.

Use `dev-server COMMAND [ARG ...]` for long-running Vite and other development
servers. New launches use the separate app-devservers.slice with 4/6 GiB
per-server thresholds and 256 MiB swap, without holding the validation lock. Hype's Vite launch scripts use this helper.
These sibling scopes remain subject to the shared development slice limits;
they isolate the editor's own allowance, not the host's total memory budget.

Use `dev-check COMMAND [ARG ...]` for heavy tests, type checks and builds,
including direct `bun x vitest` invocations. It waits for one per-user lock across
repositories and shells, then runs the command with 3/4 GiB memory thresholds,
512 MiB swap and four CPUs maximum. Nested package scripts inherit the same
lock and scope using DOTJIK_DEV_CHECK; do not set that variable manually.
Watch commands hold the slot until stopped. The runner fails closed if the user
systemd bus is unavailable; an agent sandbox must request execution with access
to that bus. Hype and Whatsover scripts route validation through this runner.
Their isolated CI runners may run without the local helper when CI=true or 1.
Direct commands that do not use the wrapper are not serialized.

Chrome DevTools MCP is disabled in managed Codex configuration by default: use
the remote runner for project checks. Its optional local launcher still uses
a pinned package and four nonblocking per-user slots.
A fifth startup exits 75 on stderr without contaminating MCP stdout. Close an
unused agent session before retrying. Each instance has a 2 GiB memory ceiling
and 256 MiB swap; closing its stdio session allows the server to exit and releases
its slot. This bounds new instances, not servers launched by earlier config.
It does not establish that previously accumulated instances were leaked.

No running editor, browser, agent or archive worker is terminated during policy
installation. Configuration applies to subsequent launches; user daemon-reload
loads the slice definition without restarting the desktop.

## Li runner

`dev-remote` uses native `tjikup ssh --transport lan li` for address discovery and
pinned host verification. No shared tailnet, exposed browser debugging port, or
new fleet deployment engine is required. Li must be awake and reachable over LAN.
The runner requires Bash, rsync, Bun, Node, GNU timeout, systemd user services and
Google Chrome on Li, plus Tjikup, Git and rsync on the submitting machine.

Run from the Git repository root:

```sh
dev-remote lint
dev-remote test
dev-remote test bun test scripts/example.test.ts
dev-remote test bash -c 'bun x svelte-kit sync && bun run check'
dev-remote --port 4173 chrome
dev-remote --port 4173 chrome bun x playwright test --config .dotjik-runner/playwright.config.mjs
dev-remote --port 4173 chrome env DEV_RUNNER_TEST_DIR=e2e bun x playwright test --config .dotjik-runner/playwright.config.mjs
dev-remote status
dev-remote cancel job-EXAMPLE
```

Defaults are `bun run lint`, `bun run test:run`, and a desktop/mobile Chrome smoke
check. Supply the complete command after the job kind to override it. All three
kinds use one shared validation lock on Li, including locally launched dev-check
jobs. This is mutual exclusion, not a strict FIFO scheduler. Waiting jobs consume
only a small service process; they do not install dependencies or launch Chrome.
Waiting is limited to 30 minutes, install to 10 minutes, command to 20 minutes,
and total service lifetime (including queueing) to 65 minutes. Job cancellation
stops the whole service cgroup and reports exit 130; abnormal disconnects remain bounded by the service
timeout. There is no automatic local fallback.

Lint/tests have MemoryHigh=3G and MemoryMax=4G; Chrome has 4G/5G. Each complete job
tree, including dependency installation and child processes, has two CPUs and
256 MiB swap maximum. The separate app-devrunner.slice has 6G/7G thresholds and
512 MiB swap maximum. It leaves room on Li's 15 GiB system for the desktop and
other services. A limit is a kill boundary, not a guarantee that a suite fits.

Every job snapshots tracked edits and nonignored new files into a unique private
directory on Li. Deleted tracked files are omitted. Source edits made after upload
do not affect that job; avoid editing during the snapshot transfer if an exact
revision is required. Git internals, node_modules, .env files, .dev.vars, Wrangler
state, generated Svelte output, and prior test reports are excluded. Ignored
fixtures/generated files must be regenerated explicitly. No local credentials or
database are implicitly copied. Symlinks are preserved, not dereferenced; external
workspace dependencies must be made self-contained. Git-dependent checks such as
staged lint should remain local. A Bun lockfile is required for package installs.

Dependencies are installed frozen with lifecycle scripts disabled, using Bun's
download cache but a separate node_modules for each job. Explicit generation such
as SvelteKit sync can be part of the submitted command. This does not forward
arbitrary local environment variables. Pass nonsecret settings through `env` in
the job command. Do not put secrets in command arguments or job logs.

Chrome uses a dedicated profile/context in visible mode on Li workspace 1 and the actual installed Google
Chrome (`channel: 'chrome'`). The supplied Playwright Test config uses visible Chrome with a job-specific X11 class, one worker,
one Chrome project and no auto-started application server. Its default testDir is
tests/e2e; set DEV_RUNNER_TEST_DIR in the remote command to change it. Existing
scripts that explicitly launch Firefox or downloaded Chromium must be adapted;
environment variables alone cannot override their launch options. Chrome smoke
checks wait for visible main content or an interactive element, then capture
desktop/mobile screenshots, page errors, HTTP status and a trace;
they are connectivity/rendering evidence, not full application acceptance tests.

Start the correct local application server once with dev-server (or the project's
managed script). `--port` creates a job-specific loopback SSH reverse tunnel to
that server on a dedicated SSH connection (no shared connection master).
PLAYWRIGHT_BASE_URL contains its remote URL. Tunnel ports come from Li's kernel ephemeral range, compatible with its SELinux
SSH bind policy. A failed bind retries up to three times before job startup;
commands that have started are never automatically rerun. Absolute localhost callback URLs,
additional API ports or host-sensitive auth may require an app-specific test
fixture; the runner does not rewrite them or copy an authenticated local browser
profile. The application server remains on the submitting machine. For apps with
a specific readiness element, pass DEV_RUNNER_READY_SELECTOR to the smoke script
in an explicit command, e.g. `env DEV_RUNNER_READY_SELECTOR=main node
.dotjik-runner/chrome-smoke.mjs`.

Results go to ~/.local/state/dev-runner/results/JOB_ID, including exit status and
logs. Custom scripts should write to DEV_RUNNER_ARTIFACTS; test-results,
playwright-report and output/playwright are also collected. Remote snapshots are
removed only after results are retrieved. Failed uploads, interrupted jobs and
failed retrievals can leave ~/.cache/dotjik-runner/jobs/JOB_ID on Li. After stopping
and retrieving an owned job, `tjikup ssh --transport lan li
'.local/bin/dev-runner-worker remove JOB_ID'` removes it. Local results are retained
until explicitly deleted.

Zed's global tasks include Li lint, tests, Chrome smoke on port 4173 and status.
The managed Codex AGENTS.md directs new sessions to the same wrapper. Restart or
refresh existing agent sessions to load it; running sessions and previously
started browsers are not changed. The Zed Biome formatter/language server remains
local; only submitted checks move to Li. Other tools that ignore the wrapper
are not automatically intercepted.

Queue status distinguishes queued, running, finished and inactive jobs, with seconds
in the reported state. Waiting submissions emit progress every 15 seconds and must
not be abandoned merely because another job owns the lock. Queue order is not FIFO.
Visible Chrome requires Li's graphical environment in the systemd user manager.
A narrow Hyprland rule places only runner Chrome windows on workspace 1 silently.
Windows close when the job finishes. Existing user windows remain untouched.
The default Hype smoke check verifies hype-local-agent-admin via get-session and
checks /admin responds successfully without redirecting away. Hype roles are hub
assignments; a generic user.role field is not used as an authorization assertion.

## Full typechecking and failure evidence

Use `dev-remote typecheck` for Hype's i18n generation, SvelteKit sync and full
svelte-check. Other Bun projects can pass their own command after `typecheck`.
This lane has MemoryHigh=5500M and MemoryMax=6G; it shares the same single heavy
slot and 7 GiB aggregate ceiling. Chrome remains at 5 GiB, tests/lint at 4 GiB.
The total service limit is 65 minutes, allowing 30 minutes queueing, 10 minutes
installation and 20 minutes checking with overhead. Status distinguishes installing
and checking from waiting. Resource samples (every 10 seconds), service journal
and a classified outcome are returned with artifacts, including for OOM kills.
Samples may miss peaks for very short jobs; the systemd journal is additional
evidence. Cancellation is not an OOM failure. Do not stop a check solely because
it is queued or approaching a memory limit. Avoid duplicate full checks for the
same snapshot; prefer focused checks when they adequately verify the change.

## Server reuse and editor recovery

New dev-server launches use app-devservers.slice, a sibling of the editor slice,
with aggregate 10/12 GiB soft/hard limits and 512 MiB swap. Each server has 4/6 GiB
limits and 256 MiB swap. Three managed server slots prevent unbounded launches.
Vite launches reuse matching checkout, persona, state, stage and normalized args;
port changes alone do not create a new server. The existing command/port is printed.
Startup is serialized by identity; existing pre-policy Vite instances can be reused.
Existing servers retain their original cgroups until stopped normally. Never stop
another thread's active server merely to acquire a slot. Existing editor sessions
are not restarted by this policy.
