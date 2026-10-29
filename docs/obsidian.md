# Obsidian and Markdown viewer

The desktop launchers have separate roles:

- **Obsidian** (`md.obsidian.Obsidian.desktop`) runs the official AppImage and opens the normal
  vault, with its community plugins. It owns `obsidian://` links.
- **Markdown Viewer** (`obsidian-appimage.desktop`) runs
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

## Launch latency

This is a standalone **profile of Obsidian/Electron**, not a separate lightweight
Markdown renderer. Both launcher entries use the same installed AppImage.

On Fi, theme preparation previously took 5.87–6.31 seconds before Electron was
executed. An unanchored selector regex repeatedly rescanned the large trailing
Style Settings comment. The one-pass tokenizer now preserves comments, quoted
strings and declarations and rewrites only selector text. Preparation measured
6.67–7.82 ms with the same installed Minimal theme. These measurements cover the
wrapper preparation, not total Electron startup or first rendered pixels.

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

On clients (`fi` and `li`), the home apply hook runs `tjikup workflow install obsidian`.
It fetches the latest stable AppImage from `obsidianmd/obsidian-releases`, verifies
the release asset's SHA-256 digest, and atomically switches
`~/.local/bin/obsidian-appimage`. Both launchers use that same verified binary.
An unsuccessful download leaves the previous binary and link intact. Existing
versions and profiles are retained. Obsidian's built-in updater can also update
the application code between AppImage releases.

The normal native profile is `~/.config/obsidian`; the former Flatpak profile is
`~/.var/app/md.obsidian.Obsidian/config/obsidian`. Uninstall Flatpak without
`--delete-data`. If migrating another client, close Obsidian and copy the Flatpak
profile to the native path only when the native profile does not already exist;
otherwise inspect both before choosing. The vault itself stays in place.

Install only these managed targets, without running unrelated hooks:

```sh
tjikup workflow install obsidian
dotjik apply
update-desktop-database ~/.local/share/applications
xdg-mime query default text/markdown
xdg-mime query default x-scheme-handler/obsidian
python3 -B -m unittest discover -s tests -p test_obsidian_viewer.py -v
```

The expected MIME defaults are `obsidian-appimage.desktop` and
`md.obsidian.Obsidian.desktop`, respectively. Regenerate `mimeinfo.cache` with
`update-desktop-database`; do not overwrite a live generated cache to install a
launcher. Test live with `obsidian-viewer /absolute/path/to/file.md`, including a
second file while regular Obsidian remains open. Run the installer before the
first launch; the viewer reports a clear error if it is absent. This setup was
launch-checked on `fi` and `li`; `si` was not exercised. Li's original Flatpak
profile was copied to the previously absent native profile before removing the
Flatpak app; the original profile and both registered vault paths were retained.

## Media Extended encrypted-login warning

During the Fi AppImage migration, Media Extended could not decrypt its
`login.json.bin` saved-login file through Electron's OS password-store API.
This concerns the plugin's saved media-site credentials, not Markdown notes,
vault contents, or the main appearance settings. A different or unavailable
password-store key can cause this; the exact key failure was not established.
The encrypted file was left intact. Media sites may require signing in again
inside the plugin if their saved login cannot be loaded; do not reset the vault.
