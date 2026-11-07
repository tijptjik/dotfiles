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
servers. It uses a separate scope with 15%/25% thresholds and 1 GiB swap without
holding the validation lock. Hype's Vite launch scripts use this helper.
These sibling scopes remain subject to the shared development slice limits;
they isolate the editor's own allowance, not the host's total memory budget.

Use `dev-check COMMAND [ARG ...]` for heavy tests, type checks and builds,
including direct `bun x vitest` invocations. It waits for one per-user lock across
repositories and shells, then runs the command with 15%/25% memory thresholds,
512 MiB swap and four CPUs maximum. Nested package scripts inherit the same
lock and scope using DOTJIK_DEV_CHECK; do not set that variable manually.
Watch commands hold the slot until stopped. The runner fails closed if the user
systemd bus is unavailable; an agent sandbox must request execution with access
to that bus. Hype and Whatsover scripts route validation through this runner.
Their isolated CI runners may run without the local helper when CI=true or 1.
Direct commands that do not use the wrapper are not serialized.

Chrome DevTools MCP uses a pinned package and four nonblocking per-user slots.
A fifth startup exits 75 on stderr without contaminating MCP stdout. Close an
unused agent session before retrying. Each instance has a 2 GiB memory ceiling
and 256 MiB swap; closing its stdio session allows the server to exit and releases
its slot. This bounds new instances, not servers launched by earlier config.
It does not establish that previously accumulated instances were leaked.

No running editor, browser, agent or archive worker is terminated during policy
installation. Configuration applies to subsequent launches; user daemon-reload
loads the slice definition without restarting the desktop.
