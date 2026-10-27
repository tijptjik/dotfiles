# Obsidian and Markdown viewer

The desktop launchers have separate roles:

- **Obsidian** (`md.obsidian.Obsidian.desktop`) runs Flatpak and opens the normal
  vault, with its community plugins. It owns `obsidian://` links.
- **Obsidian Markdown Viewer** (`obsidian-appimage.desktop`) runs
  `~/.local/bin/obsidian-viewer` and owns `text/markdown`. It uses the installed
  AppImage from `~/.local/opt/obsidian/`, opens external files in reading mode,
  and disables community and core plugins. Both sidebars start collapsed.

The viewer stores its empty vault and Electron profile under
`~/.local/share/obsidian-viewer/`. It also isolates Obsidian 1.14's CLI socket in
`$XDG_RUNTIME_DIR/obsidian-viewer/`, so opening another Markdown file cannot
route it into regular Obsidian. Files are opened in place, not copied into the
viewer vault. Reading mode is the default, not a filesystem read-only guarantee.

At each launch, the viewer copies appearance settings, installed theme, and
available enabled CSS snippets from `~/.obsidian/core/.obsidian/`. It compiles
Minimal Theme Settings and Minimal's Style Settings metadata to plain CSS,
including body class selectors, CSS variables, units, and split HSL colours.
Minimal’s table width is set to its default (content-sized) mode in the main
vault, rather than the full-width mode; the viewer inherits this setting.
It copies no plugin code, credentials, indexes, or workspace state from the main
vault. Changes to the main theme/settings appear on the next viewer launch.
Plugin-rendered content (for example Dataview queries) is unavailable by design.

## Missing plugins or custom colours

Check **Settings → Community plugins → Restricted mode** in regular Obsidian.
Plugin enablement is stored in the Electron profile's local storage, independently
of `.obsidian/community-plugins.json`. Flatpak and AppImage have distinct profiles.
On 2026-10-27, Flatpak's `enable-plugin-e0ebf70ab82d259f` was `false`, while the
AppImage's was `true`. All 55 plugins and the Minimal theme were still on disk.
Re-enabling community plugins in Flatpak restored the plugins and plugin-managed
style settings. The evidence does not establish what originally toggled that flag.
Do not restore or overwrite the vault to fix this condition.

## Installation and checks

Install only these managed targets, without running unrelated hooks:

```sh
chezmoi apply --include=files ~/.local/bin/obsidian-viewer ~/.local/share/applications/obsidian-appimage.desktop
update-desktop-database ~/.local/share/applications
xdg-mime query default text/markdown
xdg-mime query default x-scheme-handler/obsidian
python3 -B -m unittest discover -s tests -p test_obsidian_viewer.py -v
```

The expected MIME defaults are `obsidian-appimage.desktop` and
`md.obsidian.Obsidian.desktop`, respectively. Regenerate `mimeinfo.cache` with
`update-desktop-database`; do not overwrite a live generated cache to install a
launcher. Test live with `obsidian-viewer /absolute/path/to/file.md`, including a
second file while regular Obsidian remains open. The AppImage must already be
installed; the launcher reports a clear error if it is absent. This setup was
verified on `fi`; `li` and `si` were not exercised.
