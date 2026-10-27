# Rose Punk application icons

The first review set contains 25 hand-drawn SVG marks based on the launcher
screenshot, desktop startup apps and installed daily tools. This is a curated
selection, not a measured usage ranking. See [the contact sheet](rose-punk-icons-preview.svg).

The artwork uses a 64-unit grid, a dark plum `#232032` rounded surface, rose
`#e56ea1` outlines, pale lilac `#c4b5db` details and 2.6-unit rounded strokes.
App silhouettes stay identifiable at launcher sizes. All artwork is editable
in `scripts/icons/build.py`; run it to regenerate the SVGs and contact sheet.
These are original desktop theme interpretations, not official brand assets.
No image-generation service was used: these extend the repo's SVG icon system.

Source assets live under `home/dot_local/share/icons/rose-punk/`. Unique
`rose-punk-*` aliases in hicolor make them available without replacing the
distribution icons. The Rose Punk theme supplies aliases for the original
app icon names, then inherits Neuwaita and Adwaita for everything else. GTK4
and the desktop icon-theme setting select it, so Hamr recent entries using
system desktop paths receive the same artwork. `scripts/icons/apps.json` maps installed
desktop IDs, including alternate installations and the two Codex LB entries.

Managed desktop entries reference the aliases directly. For desktop entries
owned by packages, Flatpak or app installers, `scripts/icons/install.py` makes
local copies, changing only the main `Icon` field. Exec, actions, names, and
other settings are preserved. Absolute upstream icon paths are handled too.
The client-only `run_after_40-rose-punk-icons` hook runs after file deployment,
both in plain Chezmoi and in the Tjikup hook schedule. Repeated runs are safe.
Hamr may need a daemon/UI restart to refresh its app index.

Review:

```sh
xdg-open ~/.local/share/chezmoi/docs/rose-punk-icons-preview.svg
```

Installer-created overrides retain recovery data in
`~/.local/state/rose-punk-icons/desktop-overrides.json`. To undo those overrides,
run `python3 scripts/icons/install.py --restore`; it preserves entries edited
since installation. To fully retire the set, also revert the managed desktop
Icon fields and disable its apply hook, otherwise the next apply restores it.

The palette compatibility fix was committed separately; the new icon set is
left uncommitted for visual review.

## Two review directions

[Open the interactive A/B comparison](rose-punk-icons-compare.html), or view
[the static comparison sheet](rose-punk-icons-compare.svg). Each pair shows
A on the left and B on the right. The HTML preview includes 24, 32, 48, 64 and
96 px sizes and dark/light backgrounds.

- **A / Outline:** the original crisp rose and lilac line icons.
- **B / Illustrated:** filled enamel shapes, layered plum tiles, highlights and
  small relief shadows. These are editable SVG illustrations. The built-in
  image generator was unavailable, so no generated raster artwork was used.

Both sets contain all 25 apps. Original icon-name aliases and the unique
`rose-punk-*` desktop IDs resolve within the selected theme.

From the repository root, select a version for the live desktop:

```sh
python3 scripts/icons/choose.py a
python3 scripts/icons/choose.py b
```

Selection updates the managed GTK4 and dconf settings, applies the chosen
icon theme and refreshes Hamr's UI. It persists across future Chezmoi/Tjikup
runs. Other running applications may need reopening to pick up a theme switch.

Regenerate artwork and comparison assets:

```sh
python3 scripts/icons/build.py
python3 scripts/icons/illustrated.py
python3 scripts/icons/compare.py
```

B's editable rendering is in `scripts/icons/illustrated.py`; its installed
assets live in `~/.local/share/icons/rose-punk-illustrated/`. Both directions
remain uncommitted until a direction is selected for further development.
