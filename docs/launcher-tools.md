# Gitfetch and Runtjik

Gitfetch is a retained, managed client tool on Fi and Li. Chezetc's recurring
`run_56-install-launcher-tools` hook installs it when missing and checks stable
upstream releases on each apply, after the Fedora package task. It lives under
`/opt/gitfetch`, with `/usr/local/bin/gitfetch` and `~/.local/bin/gitfetch` pointing
to the active version. The combined Chez workflow includes this dependency;
there is no separate home installer. Run `gitfetch` manually to view GitHub
statistics or `gitfetch --local` for the current repository.

Runtjik is the independent Quickshell launcher in tjikOS's `apps/runtjik`.
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
The TOML config is `~/.config/runtjik/runtjik.conf`; the tjikOS app README
documents every setting, history storage, commands, and the future ZenTabs API.

`scripts/install-runtjik.sh` builds and installs the shared tjikOS source.
The regular fleet hook runs on every machine and verifies source and installed
output fingerprints before skipping an unchanged installation. Headless hosts
receive the command and files without starting a GUI. Client prerequisites are
Quickshell, Python 3.11+, PyGObject, Gio, GTK 3 and GdkPixbuf SVG support.

For an app-only installation without the full repository sync/apply workflow:

```sh
tjikup --config scripts/runtjik-install.json
```

This workflow does not commit, fetch or push repositories; it uses the existing
tjikOS checkout, so distribute/review the intended source revision first.
The installer preserves existing personal config, installs Runtjik before
retiring old Hamr services, and requires `KillMode=process` before stopping an
old GTK launcher so launched apps survive. Old config/state is retained.
Runtjik does not implement clipboard history; it does not claim Super+V.

## Duplicate desktop entries

`cleanup-launcher-entries.py --apply` removes proven obsolete shortcuts, saving
changed files under `~/.local/state/runtjik/desktop-entry-archives/` first. Tjikup's
Runtjik installer runs this cleanup and regenerates the desktop MIME cache.

- Brave ships both IDs but marks `com.brave.Browser.desktop` `NoDisplay=true`.
  Our override removed that flag. Retain the configured `brave-browser.desktop`
  and remove the local compatibility override so the RPM's hidden alias works.
- Retire `dev.zed.desktop` in favour of Zed's `dev.zed.Zed.desktop`; keep Preview
  separate. Retire the extra `com.google.Chrome.canary.desktop` in favour of the
  package's `google-chrome-canary.desktop`.
- Telegram generates `org.telegram.desktop._<MD5(binary path)>.desktop`.
  `/opt/Telegram/Telegram` produces `3e485da34fc040f9218e3891ecde1e6c`; manage that
  same ID and its MIME associations instead of producing a second shortcut.
- The older Photos and Codex LB PWA IDs were absent from FirefoxPWA's registry.
  Remove those stale shortcuts only when the registry confirms they are orphaned
  and their replacement remains registered. Never delete a live registration.
- Evince/GNOME Terminal were separately installed legacy programs. Retain
  Papers and Kitty, removing the redundant packages after
  checking the package-manager removal plan. Ptyxis was subsequently removed too:
  Kitty handles Super+Return and Runtjik terminal commands, and nothing requires
  Ptyxis. The PDF default remains Readest.

Runtjik no longer merges or relabels live duplicates. Historical statistics from
retired IDs remain associated with their surviving application. The generated
`mimeinfo.cache` is ignored by Chezmoi so stale associations are not restored.

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
