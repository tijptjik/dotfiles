# Client applications

Client policy applies to `fi` and `li`; this migration was applied and checked
locally on `fi`. Neither repository applies these changes to another host until
that host runs its normal update/apply workflow.

- Sublime Text is installed when missing by the home Chezmoi client hook. The
  official repository is configured by Chezetc; normal DNF updates maintain it.
- Obsidian uses the official, checksum-verified AppImage through the home hook.
  See [Obsidian and Markdown viewer](obsidian.md) for profile migration and the
  separate Markdown viewer. Its former Flatpak is no longer in the client list.
- VLC uses native RPMs (`vlc-cli`, `vlc-gui-qt`, and the freeworld plugins).
  The managed `org.videolan.VLC.desktop` invokes `qvlc`; its Flatpak is retired.
- Chezetc installs Font Manager from its declared COPR, Qt6 Settings from RPM,
  and Readest from Flathub. A client hook installs Zoom's official RPM when
  missing; a newer official RPM is required to update Zoom.
- GNOME applications supplied by Fedora are left alone. Lutris and its Cemu
  runner are retained.

Chrome stable is used by Hype's local headless map renderer and SaanSeoi's Atlas
browser tests. Both repositories' `playwright-cli.json` also selects Chrome for
headed sessions. Chrome Canary was retained, but no Canary-specific references
were found in either project's checked configuration/scripts.

Removal from a managed package list does not itself uninstall old copies. The
local cleanup removed the requested RPMs, Flatpaks, manual application bundles,
and stale launchers without deleting vaults or app profiles. Bitwarden's `bw`
and `bws` CLI installations are separate from its removed desktop applications.
