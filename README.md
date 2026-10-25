# Tijpfiles

Dotfiles managed by [Chezmoi](https://www.chezmoi.io/).

The system setup (repos, packages) is managed by [Chezetc](https://github.com/tijptjik/etcfiles) which needs to be setup **BEFORE** using Chezmoi.

## Supported Devices

- `fi` - Desktop (client)
- `li` - Laptop (client)
- `si` - Server

## Supported Software

Readmes are available in `/docs/{topic}.md`

- [`bat`](https://github.com/sharkdp/bat)
- [`bottom`](https://github.com/ClementTsang/bottom)
- [`codex`](https://openai.com/codex/)
- [`direnv`](https://direnv.net/)
- [`dunst`](https://github.com/dunst-project/dunst)
- [`fish`](https://fishshell.com/)
  - [`fisher`](https://github.com/jorgebucaran/fisher) - Plugin manager with automatic updates
- [`fnm`](https://github.com/Schniz/fnm)
- [`fzf`](https://github.com/junegunn/fzf)
- [`glow`](https://github.com/charmbracelet/glow)
- [GTK](https://www.gtk.org/)
- [`herdr`](https://github.com/ogulcancelik/herdr)
- [Hyprland](https://github.com/hyprwm/Hyprland)
  - [`hyprfloat`](https://github.com/nevimmu/hyprfloat)
  - [`hypridle`](https://github.com/hyprwm/hypridle)
  - [`hyprlock`](https://github.com/hyprwm/hyprlock)
  - [`hyprpaper`](https://github.com/hyprwm/hyprpaper)
  - [`hyprpicker`](https://github.com/hyprwm/hyprpicker)
  - [`hyprsunset`](https://github.com/hyprwm/hyprsunset)
  - [`hyprvoice`](https://github.com/leonardotrapani/hyprvoice)
- [`kitty`](https://sw.kovidgoyal.net/kitty/)
- [`lazygit`](https://github.com/jesseduffield/lazygit)
- [`llmtrim`](https://github.com/fkiene/llmtrim)
  - [`llmtrim-herdr`](https://github.com/fkiene/llmtrim-herdr)
- [`lsd`](https://github.com/lsd-rs/lsd)
- [`matugen`](https://github.com/InioX/matugen)
- [`micro`](https://micro-editor.github.io/)
- [`mullvad`](https://mullvad.net/)
- [`python`](https://www.python.org/)
- [`quickshell`](https://github.com/quickshell-mirror/quickshell)
- [`rclone`](https://github.com/rclone/rclone)
- [`solaar`](https://github.com/pwr-Solaar/Solaar)
- [`starship`](https://github.com/starship/starship)
- [systemd](https://systemd.io/)
- [`Tailscale`](https://tailscale.com/)
- [`tinty`](https://github.com/tinted-theming/tinty)
- [`transmission`](https://github.com/transmission/transmission)
- [`uv`](https://github.com/astral-sh/uv)
- [`vivid`](https://github.com/sharkdp/vivid)
- [`waybar`](https://github.com/Alexays/Waybar)
- [`zapzap`](https://github.com/rafatosta/zapzap)
- [`zed`](https://zed.dev/)

## Backups and recovery

The **[fleet storage atlas](docs/fleet-backup-atlas.md)** explains where files
live across Fi, Li, Si, Google and Cloudflare, with device and content icons,
backup relationships, schedules, and coverage gaps.

[![Fleet backup diagram: devices, content and recovery relationships](docs/assets/fleet-backup-atlas.png)](docs/fleet-backup-atlas.md)

- **[Read the atlas and diagram explanation](docs/fleet-backup-atlas.md)** —
  locations, content types, sync, snapshots, archives, parity and configuration.
- **[Backup map](docs/fleet-backup-map.md)** — current scopes, schedules,
  retention and coverage boundaries.
- [Device archives and cross-device restore](docs/device-archives.md) ·
  [Private-file sync and backups](docs/private-storage.md) ·
  [Server application backups](docs/si-application-backups.md) ·
  [Cloudflare backups](docs/cloudflare-backups.md)

The diagrams describe the configured backup routes and their schedules. They
are not live status dashboards; setup notes identify recovery boundaries and
remaining coverage work.

### Server media

- [Extracting archived Sonarr releases](docs/media-archive-extraction.md)

## Sample Run

<img width="891" height="609" alt="image" src="https://github.com/user-attachments/assets/f9c2f315-c573-47bc-b30d-b0d6dbff79b6" />

## Installation on New Machine

A beginning is the time for taking the most delicate care that the balances are correct.

1. **First we name her**

```bash
hostnamectl set-hostname "NAME"
```

The system-level setup is managed by [chezetc](https://github.com/tijptjik/etcfiles).

2. **Install Repos and Packages**

```bash
# Clone the chezetc repo
git clone git@github.com:tijptjik/etcfiles.git $HOME/.local/share/chezetc
# Run the setup script
$HOME/.local/share/chezetc/setup.sh
# Apply the /etc configs
$HOME/.tools/chezetc/chezetc apply
```

3. **Install required software:**

```bash
# Fedora/CentOS/RHEL
sudo dnf install kitty fish curl git chezmoi gum
```

4. **Pull in dotfiles**

```bash
# Initialize and apply dotfiles in one step
chezmoi init --apply tijptjik
```

### Tailscale and Collie on a new device

`chezetc apply` installs Tailscale, enables `tailscaled`, configures the local
user as its operator, and keeps the daemon outside Mullvad on client hosts.
Tailscale membership is deliberately not versioned: join each Linux device
interactively after applying Chezetc.

```bash
tailscale up
```

Install the Tailscale Android app and sign in to the same tailnet. On `fi`, a
subsequent `tjikup` installs/configures Collie for the local Herdr
session and reserves the tailnet-only Vite route on HTTPS port 8443. Collie is
reachable only while `fi` is locked; its Hyprlock wrapper brings the node up
after locking and takes it down again on unlock.

## Usage

Before making any changes, it is recommended to pull the latest version of the dotfiles to avoid conflicts.

### Updating

#### `tjikup`

`tjikup` is a configurable runner maintained in [tooltjik](https://github.com/tijptjik/tooltjik/tree/main/apps/tjikup). This repository supplies [the fleet workflow](tjikup.json): capture supported live settings, commit those templates, pull/push both configuration repos, then apply home and system configuration sequentially. Both repos are required. See [ownership, migration and validation](docs/tjikup.md).

Status rows use the terminal width, align notes on the right, and shorten long text with an ellipsis. Full messages remain in the run report. Child apply commands inherit the terminal width; redirected output defaults to 80 columns.

Run it after changing supported live configuration files:

```bash
tjikup
```

Use `tjikup --dry-run` to preview template changes without modifying Git or applying Chezmoi changes.

Zed propagation updates existing scalar settings and preserves template settings absent from the live config, including settings not yet applied to this host. To remove a managed setting, edit its Chezmoi template.

On clients, `chezmoi apply` (including through `tjikup`) installs or updates `codex-lb` in `~/.codex-lb/runtime`. After an update, run `systemctl --user restart codex-lb.service` between Codex sessions to activate it; the update script leaves the running proxy alone to avoid interrupting requests.

Use `tjikup --skip-conflicts` to automatically skip conflicting files during Chezmoi and Chezetc apply, preserving their local contents while applying other changes. Other apply errors still fail the command.

Apply stages stream plain output to avoid terminal capability replies leaking from Gum spinners. Interactive prompts remain available.

When Chezetc refreshes its wrapper configuration, `tjikup` shows one aligned
`CONFIG ✓ Chezetc` row and retries automatically. Routine file-path chatter is
suppressed; warnings, errors, and password prompts remain visible.

### Editing

1. **Edit a file:**

```bash
chezmoi edit $PATH_TO_FILE
```

2. **Apply changes:**

```bash
chezmoi apply
```

## Validation

Run `bash scripts/validate.sh` to check Python and non-template shell syntax and
run the isolated Tjikup regression tests. Requires Python 3 with `cryptography`
and Fish; it does not apply dotfiles, access secrets, install packages, or
synchronize Git.
Chezmoi template rendering and host-specific behavior require separate checks.

## Configuration recovery

Minimal encrypted Telegram, Brave, Steam and FirefoxPWA backups are enabled on
Fi and Li. Zen uses its own sync. uv has no separate configuration to archive;
`layout uv` selects the project's `.venv` and leaves dependency installation to
an explicit `uv sync`. Li's Chezetc fstab matches its current disks and mounts.

See the [configuration restoration guide](docs/config-restoration-plan.md) for
selected files, recovery limits and verification status.
