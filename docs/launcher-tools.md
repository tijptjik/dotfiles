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
