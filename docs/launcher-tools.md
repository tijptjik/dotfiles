# Gitfetch and Runtjik

Gitfetch remains managed by Chezetc under `/opt/gitfetch`.
Runtjik is the independent Quickshell launcher in Tooltjik's `apps/runtjik`.
It takes visual inspiration from Hamr, with a Rose Pine/Rose Punk icon grid,
an optional list, automatic desktop indexing and Fish-history command whitelisting,
local launch statistics,
and Hyprland window switching. From 0.6.0, dismissal hides the UI and keeps the
launcher warm after its first opening. Hidden instances have no mapped layer or
outside-click bindings and do not periodically refresh the index. `runtjik quit`
releases the resident processes; `/config ui.keep_alive false` restores exit on
dismissal. Reopening reloads external TOML changes.

Super+Escape toggles Runtjik on key press, independent of which key is released first. Drag its header or frame to move
the top-layer launcher card. It stays out of the normal window layout and uses
its own styling, with compositor blur, dimming and animation disabled. Enter requests a new launch; Shift+Enter switches
to a matching window or opens a titled instance picker. Tab and Shift+Tab move
through results. Outside clicks hide the launcher and reach the underlying app;
`/pin` keeps it visible after outside clicks and app launches/switches, while
remaining draggable between monitors (release on the destination screen).
`/refresh` rebuilds the index, including the command whitelist from saved Fish
history. Default search shows applications; `/run` browses previously used
commands and `/run name` filters them. GUI commands inherit application icons and
launch directly. Ctrl+L toggles grid/list.
`/shortcuts` and `/bindings` show keyboard help. `/config` browses featured
settings; for example, `/config ui.columns 6` saves TOML and applies it live.
Open/close requests are serialized and wait for readiness; failed starts exit and
report `~/.local/state/runtjik/launcher.log` instead of leaving an invisible instance.
The TOML config is `~/.config/runtjik/runtjik.conf`; the Tooltjik app README
documents every setting, history storage, commands, and the future ZenTabs API.

`scripts/install-runtjik.sh` builds and installs the shared Tooltjik source.
The regular fleet hook runs on every machine and verifies source and installed
output fingerprints before skipping an unchanged installation. Headless hosts
receive the command and files without starting a GUI. Client prerequisites are
Quickshell, Python 3.11+, PyGObject, Gio, GTK 3 and GdkPixbuf SVG support.

For an app-only installation without the full repository sync/apply workflow:

```sh
tjikup --config scripts/runtjik-install.json
```

This workflow does not commit, fetch or push repositories; it uses the existing
Tooltjik checkout, so distribute/review the intended source revision first.
The installer preserves existing personal config, installs Runtjik before
retiring old Hamr services, and requires `KillMode=process` before stopping an
old GTK launcher so launched apps survive. Old config/state is retained.
Runtjik does not implement clipboard history; it does not claim Super+V.

## GitHub release authentication

All GitHub API lookups in the Chezmoi and Chezetc installers use the common
`github_api.py` helper, bundled beside each temporary installer. This covers
Strata, Tippecanoe, Hyprvoice, Tennis, Tinty, Gitfetch, and Bitwarden's
`bw`/`bws` CLIs, including Gitfetch's release commit lookup. Keep the helper
copies in both repositories identical when changing authentication behavior.

The helper tries `GH_TOKEN`, then `GITHUB_TOKEN`, then the invoking user's
`gh auth token --hostname github.com`. Under sudo it reads that user's login
instead of root's. For normal Tjikup/Chezetc runs, use
`gh auth login --hostname github.com` as the desktop user; system hooks can
discard token environment variables while switching accounts. Unauthenticated
requests still work when no credentials are available, subject to GitHub's
anonymous API quota. Failed lookups stop the affected installer with a concise
error. Credentials stay in memory and are sent only to `https://api.github.com`;
asset downloads and Git clones retain their existing authentication behavior.

## Strata

Strata is the default file manager: `inode/directory` resolves to
`io.github.lgse.Strata.desktop`, and Hyprland's Super+E shortcut launches
`uwsm app -- strata`. Its windows use the same scrolling widths as Nautilus.

Chezetc checks GitHub's latest stable Strata release on each client apply. It
installs a newer x86_64 release under `/opt/strata/<version>` after verifying
the SHA-256 digest published in the GitHub release API, then updates
`/usr/local/bin/strata` and the compatibility link in `~/.local/bin`. Older
versioned installs remain available for rollback. Existing user settings stay
untouched; a previous user binary is saved under
`~/.local/state/chezetc/strata`. The client installer checks Fedora dependencies
on each apply.

Strata's release lookup uses the shared Chezetc updater's GitHub credentials:
`GH_TOKEN`, then `GITHUB_TOKEN`, or the desktop user's GitHub CLI login. For
normal Tjikup/Chezetc runs, authenticate with `gh auth login --hostname github.com`
as the desktop user. Without credentials, GitHub's anonymous API rate limit can
block the lookup. Authentication or rate-limit failures stop the update with an
actionable error and preserve the installed version; rerun after fixing login
or after the API limit resets. Release downloads still require the published
SHA-256 digest.

## Matugen templates

The active GTK, Micro, and Zed templates are managed by Chezmoi under
`~/.config/matugen/templates`, including the upstream license. They no longer
rely on a separate `.tools/matugen-themes` directory. Edit the managed templates
and configuration in the dotfiles repository; generated colour files stay at
the destinations specified in `~/.config/matugen/config.toml`.

## Hyprvoice

Chezetc checks the latest stable Hyprvoice release on each client apply,
verifies the downloaded binary against GitHub's release asset digest, and
activates it from a versioned `/opt` directory. Existing user configuration is
preserved.

## Tennis and Tinty

Chezetc checks each tool's latest stable release on every client apply and
verifies the archive against GitHub's published SHA-256 digest. New versions
are installed under `/opt`; older installs remain available, and the active
command links are switched after verification. Tinty settings and generated
artifacts are preserved; updates do not apply a new colour scheme.

## Bitwarden CLIs

Chezmoi checks for the latest stable `bws` and `bw` releases on each apply,
verifies their release asset digests, and activates them from versioned `/opt`
directories. The installer requires sudo for these system-owned directories.
The Secrets Manager wrapper prefers the managed command and retains a legacy
fallback while other devices migrate. Vault data and Secrets Manager
credentials stay in their existing user configuration directories.
Installation checks use isolated temporary Vault CLI state and do not log in,
unlock, or alter a vault.

Embedded Python installers are transported through Base64 in Fish hooks so
newlines and Python escapes survive template rendering exactly. A successful
Python exit alone is not treated as proof that launcher commands were installed.
