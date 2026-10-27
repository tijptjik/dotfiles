# Gitfetch and Hamr

Chezetc's client installer manages Gitfetch and Hamr in root-owned versioned
folders under `/opt/gitfetch` and `/opt/hamr`. Commands in `/usr/local/bin`
select the installed versions. Compatibility links in `~/.local/bin` replace
old executables, which are saved in `~/.local/state/chezetc/launcher-tools`.

Gitfetch uses its own Python virtual environment. Hamr includes its bundled
plugins next to the binaries; personal settings remain in `~/.config/hamr`.
The client installer validates all installed commands before publishing compatibility
links, then enables both Hamr user services and starts them when a graphical
session is active. Hyprland also starts the Hamr GTK user service at login. Super+Escape toggles the launcher;
Super+V opens its clipboard plugin. The old Quickshell startup is retired.

Hamr's expanded panel is centered on the primary displays of `fi` (1440 logical
pixels high) and `li` (1200 logical pixels high at 2× scale). The shared
`hamr-y-ratio` template allows for the 682px expanded panel: its top edge is 379px
on `fi` and 259px on `li`. Hamr 1.1.0 restores saved positions when shown, so the
position hook also updates only the primary monitor's entry in
`~/.local/state/hamr/states.json`, restarting an active GTK UI to reload it.
Other monitor positions and launcher state are preserved. Recheck the expanded
height if fonts, UI scale, or the maximum results height change.

The GTK UI includes a local layout patch in `scripts/hamr/center-modes.patch`:
list, grid, card, and form widths keep the saved horizontal center. Side previews
remain beside the centered main launcher. The correction observes GTK's actual
allocation after painting without scheduling continuous idle redraws; dragging
still saves a new center normally.

`scripts/install-hamr-layout.sh` builds only the patched GTK UI from Hamr 1.1.0's
pinned release commit and lockfile. It requires Rust/Cargo, `gtk4-devel`, and
`gtk4-layer-shell-devel`. A Chezmoi change hook rebuilds when the patch changes;
the service drop-in selects `~/.local/share/hamr-layout/hamr-gtk`. The CLI, daemon,
plugins, and upstream binaries remain managed by Chezetc. When upgrading Hamr,
review/rebase this patch and update the pinned UI revision together. To revert
the local UI, remove the `hamr-gtk.service.d/layout.conf` drop-in, reload systemd,
and restart `hamr-gtk.service`.

`tjikup` checks GitHub for each tool's latest stable release and updates the
versioned install when needed. Hamr archives are verified against the release
asset digest. Gitfetch is installed from the latest stable release tag after
checking that the cloned commit matches GitHub's commit API. Reproducible
downloads and build output do not require recurring backups. Preserve personal
configuration.

## GitHub release authentication

All GitHub API lookups in the Chezmoi and Chezetc installers use the common
`github_api.py` helper, bundled beside each temporary installer. This covers
Strata, Tippecanoe, Hyprvoice, Tennis, Tinty, Hamr, Gitfetch, and Bitwarden's
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
