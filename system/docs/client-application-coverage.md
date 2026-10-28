# Client application coverage

`packages.client` declares Chrome stable, mpv, native VLC, retained Fedora GNOME
apps, and the selected Flatpaks, including Plex Desktop and Lutris. `ov` is in
`packages.common` because Fish sets `PAGER=ov` on every host.

Chrome is bootstrapped from Google's official RPM before the package phase;
the hook also enables Google's update repository, including Fedora's disabled
repository definition. Subsequent DNF updates maintain Chrome stable. It is used by local Playwright rendering and browser tests.

Plex Desktop is `tv.plex.PlexDesktop` from Flathub. Its build manifest downloads
the Linux desktop tarball from `downloads.plex.tv`; this is the desktop client,
not the `plexmediaserver` server package. Native VLC and mpv are retained as
independent playback engines.

## Components managed outside package lists

| Component | Owner |
| --- | --- |
| Bitwarden `bw` and `bws` CLIs | Home Chezmoi `run_before_02-install-bws.fish.tmpl` and `install-bitwarden-cli.py`; needed during home/bootstrap setup |
| Lutris application | Chezetc's `net.lutris.Lutris` Flatpak entry |
| Cemu and other downloaded Lutris runners | Lutris; runner versions and game configuration stay with Lutris data |
| Sublime Text | Home client install hook, official RPM repository managed by Chezetc |
| Obsidian AppImage | Home client install hook, verified against official release asset checksum |

Do not install duplicate Bitwarden desktop apps or a second system Cemu merely
to duplicate this coverage. Preserve Lutris runner/game data during app cleanup.
Retired desktop app profiles remain available for recovery. Li's Touch bottle
(TouchDesigner and TouchPlayer) and its user-settings backup were deleted at
the user's request.
The `mtr`, `iptstate`, `pinfo`, and `tmux` commands are not required by current
tools or aliases. Fish's `done` plugin detects tmux only when it is installed.

Li uses the Lutris Flatpak with its original native config/data directories
symlinked into the Flatpak paths. Its Wine runner remains accessible. Cemu was
present on Fi only; no Cemu runner was found on Li.

Azahar is retired from the client Flatpak policy. A stale declaration previously
reinstalled it during routine maintenance after its manual removal. Keep it out
of `packages.client.flatpak.flathub`; remove any reintroduced installation with
`sudo flatpak uninstall --system org.azahar_emu.Azahar` while retaining the app's
profile and save data (do not use `--delete-data`).
