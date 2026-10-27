# Bartjik

Bartjik is the desktop bar on `fi` and `li`. Its configuration is managed in
`home/dot_config/bartjik/config.json.tmpl`; tjikOS owns its runtime.

Every `tjikup` home apply runs `run_after_39-install-bartjik.fish.tmpl`, which
builds and installs only Bartjik using `scripts/install-bartjik.sh`. It uses
`TJIKOS_REPO` when set, otherwise `~/code/tjikos` on every host. Missing
checkouts are cloned there; existing checkouts are never pulled by installers.
Older `~/.local/share/tjikos` checkouts require the migration described in
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
The workspace preview overlay has two solid bottom notches showing app icons for tiled
scrolling windows outside the previewed workspace's viewport. The left notch shows
windows offscreen to the left; the right notch shows those to the right. Each notch
appears only when its side has items, with a gap between the two sides. Each
window gets an icon, ordered by its position in the strip. Visible windows,
floating windows and other workspaces are excluded. A border sliver of eight
logical pixels or less counts as offscreen. Both notches disappear when empty.
Set `modules.spaces.offscreen` to `false` to hide it.
Click an offscreen icon to focus that exact window, slide the workspace to it,
and close the preview.

The managed `~/.local/bin/quickshell` wrapper selects the shared `RosePunk` Qt
Quick Controls style from `~/.local/share/quickshell/styles/`. Bartjik, Notjik and
Runtjik opt into it with `//@ pragma RespectSystemStyle` in their shell roots;
Quickshell otherwise forces Fusion and ignores the requested style. This gives even
attached `ToolTip` popups the dark rounded background, border, text and font by
default, across Quickshell apps launched through `quickshell`. Other controls
fall back to Fusion. App-specific themed tooltips can override these defaults;
an explicit `QT_QUICK_CONTROLS_STYLE` also takes precedence. Launching
`/usr/bin/quickshell` directly bypasses the wrapper.
On `li`, the tray is the first island on the left, crypto is hidden, and the
AI island shows only Codex quota to keep the layout compact.

Signal and Zoom use managed outline tray icons, matching the existing monochrome
messenger icons at 18 pixels. `modules.tray.iconOverrides` selects these SVGs by
application ID or title when the applications register their tray items. Apply
the Bartjik config and `signal-outline.svg` / `zoom-outline.svg` in
`~/.local/share/icons/hicolor/scalable/apps/` together; Bartjik reloads the
configuration without restarting the applications.
