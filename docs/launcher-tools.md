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

`tjikup` checks GitHub for each tool's latest stable release and updates the
versioned install when needed. Hamr archives are verified against the release
asset digest. Gitfetch is installed from the latest stable release tag after
checking that the cloned commit matches GitHub's commit API. Reproducible
downloads and build output do not require recurring backups. Preserve personal
configuration.

## Strata

Chezetc checks GitHub's latest stable Strata release on each client apply. It
installs a newer x86_64 release under `/opt/strata/<version>` after verifying
the SHA-256 digest published in the GitHub release API, then updates
`/usr/local/bin/strata` and the compatibility link in `~/.local/bin`. Older
versioned installs remain available for rollback. Existing user settings stay
untouched; a previous user binary is saved under
`~/.local/state/chezetc/strata`. The client installer checks Fedora dependencies
on each apply.

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
