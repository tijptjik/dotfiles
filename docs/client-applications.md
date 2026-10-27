# Client applications

Client policy applies to `fi` and `li`; this migration was applied on both hosts.
Other hosts receive source changes only through their normal update workflow.

- Sublime Text is installed when missing by the home Chezmoi client hook. The
  official repository is configured by Chezetc; normal DNF updates maintain it.
- Obsidian uses the official, checksum-verified AppImage through the home hook.
  See [Obsidian and Markdown viewer](obsidian.md) for profile migration and the
  separate Markdown viewer. Its former Flatpak is no longer in the client list.
- VLC uses native RPMs (`vlc-cli`, `vlc-gui-qt`, and the freeworld plugins).
  The managed `org.videolan.VLC.desktop` invokes `qvlc`; its Flatpak is retired.
  A hidden `vlc.desktop` compatibility entry avoids a duplicate menu item while
  retaining old MIME associations on hosts with the native `vlc` package.
- Chezetc installs Font Manager from its declared COPR, Qt6 Settings from RPM,
  and Readest from Flathub. A client hook installs Zoom's official RPM when
  missing; a newer official RPM is required to update Zoom.
- Retained GNOME applications are explicit in Chezetc's client package list.
- Chrome stable is managed on all clients. Its hook installs the official RPM
  when absent and enables Google's update repository. It supports Hype's local
  renderer, SaanSeoi's Atlas browser tests, and both projects' headed Playwright
  sessions.
- mpv is an alternate playback engine alongside native VLC. Plex Desktop uses
  Flathub's `tv.plex.PlexDesktop`, whose manifest downloads the official Linux
  desktop archive from `downloads.plex.tv`.
- `ov` is retained and explicitly managed because Fish sets `PAGER=ov`.
  `mtr`, `iptstate`, `pinfo`, and `tmux` were removed from both clients after
  checking tools, aliases, and package dependencies. Fish's optional tmux
  integration is guarded and does not require tmux.

On Li, the selected extra RPM apps, Beta browser channels, Flatpaks, manual
application bundles, and Kimi AI PWA were removed. App profiles and wallet data
were retained. The removed Bottles app's `Touch` bottle, including TouchDesigner
and TouchPlayer 2025.33070, was subsequently deleted at the user's request. The
remaining 16 MB user-settings backup was also deleted at the user's request.

Bitwarden's `bw` and `bws` CLIs remain owned by the home bootstrap hook, while
Chezetc declares the Lutris Flatpak. Lutris owns its downloaded emulator runners
and game data. See Chezetc's `docs/client-application-coverage.md` for the ownership
table. Neither machine's vault or gaming data should be treated as app binaries.

Li's duplicate native Lutris RPM was removed after connecting its retained
`~/.config/lutris` and `~/.local/share/lutris` directories to the Flatpak's
configuration and data paths with symlinks. Access to its Wine runner was checked
inside the Flatpak. Cemu remains on Fi; no Cemu runner was installed on Li.
