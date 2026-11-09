# Herdr App, Zed and Android

Research checked against upstream documentation on 2026-11-09. Live fleet and
Android behavior has not been validated.

## Fleet installation

`home:herdr-app` installs Herdr Core (`herdr-core`, normally also `hc`) and Herdr
App (`herdr-app`) for the normal user on Fi, Li and Si. It is a required install
recipe, so existing device subscriptions do not need editing. It uses the
official Core and App installers, which verify release archive SHA-256 hashes.
Existing binaries are retained; this is first-install provisioning, not an
automatic runtime migration or upgrade. App has its own updater; Core provides
`herdr-core update` for separately scheduled updates.

The App requires a desktop session and working Vulkan driver on Linux. Si gets
the binaries, but its useful headless component is Core: connect to Si over SSH
from App on Fi or Li. Installation does not launch either component. The
existing `herdr` binary, plugins, saved sessions and Collie service are retained.
Neither App nor Core imports the old session snapshot through this policy.
An unrelated existing `hc` command is left to the upstream installer's collision
handling; `herdr-core` is the unambiguous command.

Sources: [App](https://github.com/herdrdev/herdr-app),
[App installer](https://github.com/herdrdev/herdr-app/blob/master/distribution/install.sh),
[Core](https://github.com/herdrdev/herdr-core).

## Community integrations

| Project | What it connects | Important limit |
| --- | --- | --- |
| [Zerdr](https://github.com/ryonakae/zerdr) | Herdr workspace focus to Zed Git checkouts; Zed terminal threads to persistent Herdr panes | Targets legacy Herdr 0.8+, Zed 1.15+ and terminal threads. Runtime commands require local macOS/Linux; SSH is rejected except detach/hooks. No documented App/Core support. |
| [Zed Workspace Sync](https://github.com/ImArtisann/zed-herdr) | Legacy Herdr workspace events to `zed -e <git-root>` | Workspace focus only, not thread synchronization. Requires Herdr protocol 16+, tested through 22, Bun and Git. |
| [herdr-zed-layout](https://github.com/dantech99/herdr-zed-layout) | A Zed-inspired layout/mod set inside Herdr App | Visual layout, files and Git panels; not a bridge to Zed's workspaces or conversations. |
| [Collie](https://github.com/AltanS/collie) | Android/browser control of terminals through a host bridge | Supports separate `herdr` and `herdr-core` adapters. One backend per instance; not a Zed GUI remote-control protocol. |

Do not install both workspace routers together: they would independently route
Zed focus. None of these establishes synchronization of Zed's native agent-chat
history, access permissions, or every workspace on other machines. Zerdr's
thread integration specifically means **terminal threads** attached to the same
running terminal, not copying conversation databases. Existing native chats
would need an explicit handoff to an agent running in a shared terminal.

## Recommended remote path

For the new App, use **Android Collie PWA → Tailscale HTTPS → Collie with
`COLLIE_MUX=herdr-core` → Core terminals**, with App viewing those same terminals
on the desktop. Current Collie supports this adapter; the repository's existing
Collie provisioning still targets the legacy plugin and socket. Do not simply
change its backend while old sessions remain in use. Prepare a separate named
Collie instance with distinct configuration, state, service and port, or migrate
the existing instance after its sessions have been handed over. Preserve the
current trusted-user restriction and device pairing.

For Zed terminal-thread sharing today, the documented community route is
**Collie legacy backend → legacy Herdr panes ← Zerdr ← Zed terminal threads**.
Run `zerdr setup install` locally on the Zed desktop, then `zerdr connect` inside
a Zed terminal thread. `zerdr start` additionally enables workspace routing;
`zerdr setup auto enable` opts new terminal threads into attachment and changes
Zed settings. These setup commands are not run by Dotjik: App/Core compatibility
is not documented, and the legacy integration needs a local interaction trial
before becoming fleet policy. Zerdr supports detaching a desktop thread to let
a phone-sized client take over a pane, then reattaching when returning to Zed.

For a direct fallback with the new runtime, SSH from an Android terminal client
to the host and use `herdr-core ls`, then `herdr-core attach <terminal-address>`.
Use an address from the live listing. This controls the shared agent terminal;
controlling the entire Zed GUI requires a separate remote-desktop solution.

On Android, join the same tailnet, open the Collie HTTPS URL in Chrome, pair the
device, and use Settings → Install (or Chrome → Add to home screen → Install).
See [Collie install](https://github.com/AltanS/collie/blob/main/docs/install.md),
[multiplexers](https://github.com/AltanS/collie/blob/main/docs/multiplexers.md),
and [multiple instances](https://github.com/AltanS/collie/blob/main/docs/deployment.md#multiple-collie-instances-on-one-host).

Before migration, verify on one desktop that a disposable agent is visible in
App and Collie, phone input reaches the correct terminal, desktop disconnect
does not stop it, and reconnect preserves its identity. Test Zed thread
attachment separately with the legacy runtime. Pairing requires the actual
phone; rendering templates and installer mocks cannot prove this end-to-end path.
