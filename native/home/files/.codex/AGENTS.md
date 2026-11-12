# Managed development checks

For Bun/Svelte repositories on the managed desktops, run heavy checks on Li via
`dev-remote` from the Git root. It sends tracked edits and nonignored new files to
an isolated snapshot, queues across agents, and returns artifacts outside the
checkout. Use `dev-remote lint`, `dev-remote test`, or provide an explicit command:
`dev-remote test bun test path/to/test.ts`. Ignored files, secrets and local databases
are not copied. Explicitly generate required ignored build outputs in the job.

For application browser checks, start the intended local dev server once, then use
`dev-remote --port 4173 chrome` for desktop/mobile smoke evidence. For interaction
tests use `dev-remote --port 4173 chrome bun x playwright test --config
.dotjik-runner/playwright.config.mjs`; the default test directory is tests/e2e.
Use `env DEV_RUNNER_TEST_DIR=relative/path` before the command to select another
directory. Test real Google Chrome (`channel: 'chrome'`), not Firefox. Custom browser
scripts must use visible Chrome on Li workspace 1, with the managed launch options, and write evidence to DEV_RUNNER_ARTIFACTS.
Smoke screenshots do not prove application interaction correctness.

Use `dev-remote status` and `dev-remote cancel JOB_ID` to inspect or stop owned jobs.
Never silently fall back to local browsers when Li is unavailable. Do not start
local Chrome MCP for project testing or leave idle browser sessions running.
For checks requiring local state or non-Bun tooling, use `dev-check COMMAND ...`;
it shares a local lock and enforces a 4 GiB ceiling. Do not set DOTJIK_DEV_CHECK
manually, bypass failed scopes, or hold validation slots with watch commands.

A busy validation slot is not a reason to skip browser verification. Submit the job
and wait for completion; the runner reports queue progress every 15 seconds. Use
`dev-remote status` to distinguish queued and running jobs. Report a concrete
queue timeout, cancellation, or failed test if verification cannot complete.
The default Hype smoke command verifies the local admin identity and /admin access.
Custom tests must make equivalent auth assertions when testing admin behavior.

Use `dev-remote typecheck` for full Hype Svelte validation (6 GiB maximum), not
the 4 GiB test lane. Other projects can supply their typecheck command explicitly.
Do not cancel a queued or memory-busy job merely to finish a turn. Wait for its
exit, unless the user requests cancellation or there is a concrete safety issue.
Use artifacts/outcome.txt, resources.txt and service.log to distinguish diagnostic
failures, cancellation, timeouts and OOM kills. Do not label pressure as OOM.
Prefer focused tests for a narrow change; do not submit duplicate full validation
for the same source snapshot while an equivalent check is already active.

Reuse the existing development server for the same checkout/persona. `dev-server`
reports the existing command/port instead of launching a duplicate. Do not bypass
it or choose a new port to evade reuse/capacity limits. Separate checkouts or
personas can need distinct servers; stop owned unused instances when finished.
