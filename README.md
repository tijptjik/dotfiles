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
- [`tinty`](https://github.com/tinted-theming/tinty)
- [`transmission`](https://github.com/transmission/transmission)
- [`uv`](https://github.com/astral-sh/uv)
- [`vivid`](https://github.com/sharkdp/vivid)
- [`waybar`](https://github.com/Alexays/Waybar)
- [`zapzap`](https://github.com/rafatosta/zapzap)
- [`zed`](https://zed.dev/)

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

## Usage

Before making any changes, it is recommended to pull the latest version of the dotfiles to avoid conflicts.

### Updating

#### `tjikup`

`tjikup` synchronizes supported live configuration changes back into their Chezmoi templates. It then commits the updated templates, pulls and pushes the dotfiles repository, applies the changes with Chezmoi, and updates the Chezetc repository when available.

Run it after changing supported live configuration files:

```bash
tjikup
```

Use `tjikup --dry-run` to preview template changes without modifying Git or applying Chezmoi changes.

### Editing

1. **Edit a file:**

```bash
chezmoi edit $PATH_TO_FILE
```

2. **Apply changes:**

```bash
chezmoi apply
```

## TODO

### Config

- [DirEnv for UV](https://github.com/direnv/direnv/issues/1250)
- Telegram
- Once zed implements [modelines support](https://github.com/zed-industries/zed/issues/4762), update the `tmpl` files with proper syntax hints

### Laptop

- `fstab`

### Packages Not Backed Up

- .zen/
- .config/BraveSoftware
- .config/Steam
- .config/uv
- .local/share/firefoxpwa
