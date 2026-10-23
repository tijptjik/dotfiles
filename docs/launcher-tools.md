# Gitfetch and Hamr

Chezetc's client installer manages Gitfetch and Hamr in root-owned versioned
folders under `/opt/gitfetch` and `/opt/hamr`. Commands in `/usr/local/bin`
select the installed versions. Compatibility links in `~/.local/bin` replace
old executables, which are saved in `~/.local/state/chezetc/launcher-tools`.

Gitfetch uses its own Python virtual environment. Hamr includes its bundled
plugins next to the binaries; personal settings remain in `~/.config/hamr`.
Hyprland starts the Hamr GTK user service. Super+Escape toggles the launcher;
Super+V opens its clipboard plugin. The old Quickshell startup is retired.

`tjikup` runs the idempotent Chezetc installer. Versions and source checksums
are pinned in `.chezmoitemplates/install-launcher-tools.py` in the Chezetc repo;
change those pins deliberately to upgrade. Reproducible downloads and build
output do not require recurring backups. Preserve personal configuration.

## Strata

Chezetc installs Strata 1.0.0 under `/opt/strata/1.0.0` from its checksum-pinned
upstream release. `/usr/local/bin/strata` and the compatibility link in
`~/.local/bin` select that binary. Existing user settings remain untouched;
the previous user binary is saved under `~/.local/state/chezetc/strata`.
The client installer checks Fedora dependencies on each apply. Upgrade the
version and checksum in `run_53-install-strata.fish.tmpl` deliberately.

## Matugen templates

The active GTK, Micro, and Zed templates are managed by Chezmoi under
`~/.config/matugen/templates`, including the upstream license. They no longer
rely on a separate `.tools/matugen-themes` directory. Edit the managed templates
and configuration in the dotfiles repository; generated colour files stay at
the destinations specified in `~/.config/matugen/config.toml`.

## Tennis and Tinty

Chezetc installs Tennis 0.6.0 and Tinty 0.30.0 into versioned `/opt` directories,
with commands in `/usr/local/bin`. The client hook
`run_57-install-terminal-tools.fish.tmpl` pins release URLs and SHA-256 checksums.
The migration preserves existing versions and Tinty settings and generated
artifacts; it does not apply a new colour scheme.

## Bitwarden CLIs

Chezmoi's early bootstrap installs checksum-pinned `bws` 1.0.0 and `bw`
2025.11.0 under `/opt/bws` and `/opt/bw`, with commands in `/usr/local/bin`.
The installer requires sudo for these system-owned directories. The Secrets
Manager wrapper prefers the managed command and retains a legacy fallback
while other devices migrate. Vault data and Secrets Manager credentials stay
in their existing user configuration directories. Installation checks use
isolated temporary Vault CLI state and do not log in, unlock, or alter a vault.
