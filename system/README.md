# System configuration in Dotjik

This directory contains the former Systjik checkout, including its in-progress
recipe migration. It is part of `tijptjik/dotfiles` and is not a separate Git sync
target. Read [the unified workflow guide](../docs/tjikup.md#native-file-migration)
for current commands, native file ownership and recovery. Chezetc is no longer a
dependency; Chezmoi remains a temporary renderer for unported templates.

The following original guide is retained as historical provisioning context.
Do not follow its separate-checkout or Chezetc installation instructions for
routine updates.

---

# Systjik

System configuration managed by Chezetc. Use `systjik` as the command name
after installing Dotjik; `chezetc` continues to work. The GitHub repository
is `systjik` and the checkout lives at `~/.local/share/systjik`.

Setup the system environment before running the [dotfiles](https://github.com/tijptjik/dotfiles) setup with chezmoi.

## Manages

- DNF Repositories
- Tailscale package and daemon lifecycle
- [SSH connection reuse](docs/ssh-connections.md) for Git and fleet access
- Packages
  - RPM
  - Flatpak
- Fedora release upgrades, with a seven-day reminder after declining an available release
- Bartjik is installed and started by the home Chezmoi apply hook.
- Local builds that are temporarily required for upstream compatibility
  - The server builds the WebDAV extension as a local RPM from the pinned
    `nginx-dav-ext-module` v3.0.0 source. It uses Fedora's `nginx-mod-devel`
    sources and rebuilds after system updates, so it stays aligned with Fedora
    Nginx without the GetPageSpeed repository. Fedora's automatic live-upgrade
    trigger is held until the rebuilt module passes `nginx -t`; Chezetc then
    upgrades the running master or starts Nginx if it was inactive. The ABI is read
    from the installed `nginx -v` binary, so duplicate RPM records after an
    interrupted update cannot produce a combined version string. A current
    module is accepted only when the full `nginx -t` check passes, including
    the stream module; rebuilding requires matching Fedora header macros.
- Si application updates: changed Docker images and session-aware Plex RPM
  updates, with a recent-backup requirement. See [Si app updates](docs/si-app-updates.md).
- `fstab`

## Client desktop applications

The client list provisions Font Manager (with its COPR), Qt6 Settings, and
native VLC (including its Qt GUI). Readest uses Flatpak. Zoom is installed from
its official RPM by a client-only hook because it has no DNF repository;
existing Zoom installs are retained and updates remain manual/in-app. Obsidian uses the official AppImage
installed by the home Chezmoi hook; Sublime Text is also installed by a home
client hook using the official RPM repository managed here. Do not restore the
Obsidian or VLC Flatpak entries: their native launchers are managed in the home
checkout. Removing an entry does not uninstall existing copies; migrate profiles
and remove redundant installations explicitly.

Material Symbols Rounded is bundled with Bartjik in tjikOS and loaded directly
by Qt. It no longer needs the `material-symbols-fonts` RPM or
`purian23/material-symbols-fonts` COPR. The COPR hook retires that repository and
its enabled-state override, while leaving the old RPM installed until the
bundled font has been verified on the host. COPR setup accepts only the host's
native Fedora release; it never chooses an older release as a fallback.
Already configured disabled COPRs stay disabled.

## Fedora repository ownership

On Fedora 45 and later, Fedora and Chrome repo definitions are supplied under
`/usr/share/dnf5/repos.d`. Chezetc ignores its legacy copies of `fedora.repo`,
`fedora-updates.repo`, `fedora-cisco-openh264.repo`, and `google-chrome.repo` in
`/etc/yum.repos.d`, so applies do not recreate obsolete overrides. Si and Li's
package-owned definitions were identical when reconciled; Chrome is disabled.
The existing Docker package exclusions are retained in
`/etc/dnf/repos.override.d/60-chezetc-docker.repo` for the six Fedora/updates
repositories that previously carried them. Fedora 44 continues to use the
existing managed repo files until upgraded.

When reviewing future repo prompts, compare both `/etc/yum.repos.d` and
`/usr/share/dnf5/repos.d`; do not restore `.rpmsave` files over vendor definitions.
The ignore rules leave any existing `/etc` overrides untouched. Si and Li had
none of these four overrides when this policy was added.

## Supported Hosts

- `fi` : Desktop
- `li` : Laptop
- `si` : Server

## Setup

This script will (1) install required dependencies, (2) clone the `chezetc` repo to `$HOME/.tools/chezetc`, (3) install the configuration to `$HOME/.config/chezetc/chezetc.toml`.

```sh
git clone git@github.com:tijptjik/systjik.git $HOME/.local/share/systjik
$HOME/.local/share/systjik/setup.sh
```

Now you can manage your `/etc` files with `chezetc`.

Fleet preparation and hook rendering prefer the managed `/usr/local/bin/chezetc`
launcher (or `/opt/chezetc/chezetc` directly) over older wrappers in PATH. The
managed wrapper preserves the fleet's system-hook deferral flag through sudo,
so file preparation cannot accidentally execute the later update hooks.

```sh
# chezetc is added to the path in the dotfiles, so it is not
# available before you've set them up with chezmoi.
/opt/chezetc/chezetc apply
```

## Validation

Run `bash scripts/validate.sh` with Bash, Fish, and Python 3 installed. It checks
shell syntax and tests setup with isolated paths and stubbed install commands.
If Chezmoi and its configuration are available, it also renders Fish script
templates for the current host without executing them. Set `CHEZETC_CONFIG` to
use a different configuration. Skipped rendering is reported explicitly.

## Todo

- Reenable Sublime Text, once the [GPG key digest issue is fixed](https://discussion.fedoraproject.org/t/sublime-text-not-able-to-install-in-fedora-43/170396/8)

## Server recovery and reproducibility

See [SERVER-REBUILD.md](SERVER-REBUILD.md) for the service inventory, version-control boundaries, storage guards, restore order, and remaining work toward unattended provisioning. Do not use a blanket apply as a fresh-server recovery procedure yet.

## Client login and screen locking

Chezetc manages `/etc/gdm/custom.conf`: fi and li automatically log in as `io`.
Their home configuration enables `hyprlock-login.service` with the graphical
session, after Hyprland exports its Wayland display. The service launches
`~/.local/bin/tailscale-lock`, which starts Hyprlock. Install and verify that
home configuration before relying on autologin; GDM does not itself wait for
Hyprlock to acquire the session lock.

Select **Hyprland (uwsm-managed)** for the account's saved GDM session. Confirm
`systemctl --user is-enabled hyprlock-login.service` and that `/usr/bin/hyprlock`
and `~/.local/bin/tailscale-lock` exist. Apply the GDM file narrowly with
`chezetc apply --exclude scripts /etc/gdm/custom.conf`. It takes effect on the
next boot/login; do not restart GDM inside a working desktop session.

On fi and li, `run_58-hyprland-gdm-session.fish.tmpl` installs a local override at
`/usr/local/share/wayland-sessions/hyprland-uwsm.desktop`. It preserves the saved
session ID and the package-owned entry, but starts UWSM with `-g -1` so it does
not wait for `graphical.target`. During GDM autologin, that target can be held
by `plymouth-quit-wait.service`; waiting lets the greeter take over before
Hyprland acquires its seat. The hook first compares the installed entry with
the desired content and checks its root ownership and 0644 permissions. It
reports SKIP when already configured; otherwise it validates and repairs the
entry, reports CONFIG, and never restarts GDM. Apply only this hook with:
`chezetc --source ~/.local/share/chezetc/etc apply --source-path ~/.local/share/chezetc/etc/.chezmoiscripts/run_58-hyprland-gdm-session.fish.tmpl`.
Verify the next boot reaches Hyprlock without a GDM password prompt. To roll
back, remove the local override with `sudo rm /usr/local/share/wayland-sessions/hyprland-uwsm.desktop`
and disable the hook before the next Chezetc apply. si does not install
this override.

The server retains its existing automatic login as `m`.


### Persistent client tailnet

Fi and Li keep their enrolled Tailscale connections available after boot,
apply, lock, and unlock. The Tailscale hook enables `tailscaled`, sets the
interactive user as operator, preserves Mullvad DNS/default-route ownership
with `--accept-dns=false --accept-routes=false`, and resumes a stopped enrolled
client. It reports missing enrollment without attempting an automatic login.
`tailscale up` persists the running preference for the next daemon start.
The daemon uses the managed Mullvad split-tunnel cgroup override. The home
`tailscale-lock` compatibility command now only runs Hyprlock.

Home-managed `sshfi`/`sshli` discover peers through the Tailscale API, prefer
IPv6 tailnet addresses, and fall back to Avahi LAN discovery. They retain
OpenSSH authentication and pinned host identities; Tailscale SSH stays disabled.
See the dotfiles `docs/tailscale-setup.md` for route selection and diagnostics.

### Hyprvoice (clients)

Chezetc checks the latest stable upstream x86_64 release on each apply and installs
it into `/opt/hyprvoice/<version>/hyprvoice`, verifying its SHA-256 before installation.
`/usr/local/bin/hyprvoice` and the desktop user's `~/.local/bin/hyprvoice`
point to that binary. Existing unmanaged user binaries are preserved under
`~/.local/state/chezetc/hyprvoice/`. User configuration, shortcuts and the user
service remain managed by the home Chezmoi repository. The installer does not
restart a running dictation session. The source checkout in `~/.tools` is not required.

All GitHub API lookups for Strata, Tippecanoe, Hyprvoice, Tennis, Tinty,
Gitfetch (including commit lookup), and the home repository's Bitwarden CLIs
use the shared `github_api.py` helper, bundled beside each temporary installer.
Keep the helper copies in both repositories identical. It authenticates metadata
requests using `GH_TOKEN`, then `GITHUB_TOKEN`, when available in the installer
environment, otherwise the desktop user's `gh auth token --hostname github.com`.
For normal Tjikup/Chezetc runs, use `gh auth login --hostname github.com` as the
desktop user: the system hook returns to that user's account before the lookup.
Installers that run under sudo retrieve the invoking user's GitHub CLI login
instead of root's. Tokens are not logged, persisted by the updater, or sent with
asset downloads. Authenticated requests and redirects stay on `api.github.com`.
Without credentials, public release lookups remain available subject to GitHub's
anonymous rate limit. Authentication and rate-limit failures remain errors and
leave the affected tool's active installation in place; rerun after fixing login
or waiting for the limit to reset.

### Tippecanoe (clients)

Every Tjikup apply checks the latest stable `felt/tippecanoe` GitHub release.
Chezetc builds a new release in temporary storage, runs upstream unit tests and
creates a sample MBTiles archive before installing into `/opt/tippecanoe/<tag>`.
The six tools are exposed through `/usr/local/bin`; existing unmanaged executables
are never overwritten. Matching installations are reused. Previous release
directories remain available for rollback. A network or build failure is reported
and leaves the active installation in place. No `.tools` source checkout is needed.
