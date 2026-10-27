# Bartjik

Bartjik is the desktop bar on `fi` and `li`. Its configuration is managed in
`home/dot_config/bartjik/config.json.tmpl`; Tooltjik owns its runtime.

Every `tjikup` home apply runs `run_after_39-install-bartjik.fish.tmpl`, which
builds and installs only Bartjik using `scripts/install-bartjik.sh`. It uses
`TOOLTJIK_REPO` when set, otherwise `~/code/tooltjik` on every host. Missing
checkouts are cloned there; existing checkouts are never pulled by installers.
Older `~/.local/share/tooltjik` checkouts require the migration described in
[Tjikup](tjikup.md). Quickshell and Python 3 must already be installed.

The installer restores the managed Fish service wrapper, reloads systemd and
enables Bartjik. It starts the service in an active graphical session; headless
runs leave startup to the next graphical login. Active Bartjik sessions are
not restarted during routine applies.

After installation succeeds, the migration masks the Waybar user service,
stops directly launched Waybar and its old audio/network panels, and moves
old configuration and the custom launcher/runtime into timestamped directories
under `~/.local/state/bartjik/migration/`. This preserves local crypto data.
Repeated runs do not create new backups unless legacy files reappear.
The retired Quickshell `network` and `audio` directories are explicitly ignored
by Chezmoi, including on clients. Leftover source-tree Python caches must not
recreate those directories and trigger conflict prompts after migration.
Tinty no longer launches Waybar, and Chezetc no longer installs or builds it.
The archived source/build caches and any already-installed distro package are
inert; the Waybar service remains masked.

For a focused repair without fleet Git or system updates:

```sh
bash ~/.local/share/chezmoi/scripts/install-bartjik.sh
systemctl --user status bartjik.service
journalctl --user -u bartjik.service -n 50
```

Bartjik uses its bundled rose-punk theme. `hrcb` edits its managed JSON config.
The bars auto-hide: move the pointer to the bottom edge to reveal them.
On `li`, the tray is the first island on the left, crypto is hidden, and the
AI island shows only Codex quota to keep the layout compact.

Signal and Zoom use managed outline tray icons, matching the existing monochrome
messenger icons at 18 pixels. `modules.tray.iconOverrides` selects these SVGs by
application ID or title when the applications register their tray items. Apply
the Bartjik config and `signal-outline.svg` / `zoom-outline.svg` in
`~/.local/share/icons/hicolor/scalable/apps/` together; Bartjik reloads the
configuration without restarting the applications.
