# Tijpfiles
Dotfiles managed by [Chezmoi](https://www.chezmoi.io/).

The system setup (repos, packages) is managed by [Chezetc](https://github.com/tijptjik/etcfiles) which needs to be setup **BEFORE** using Chezmoi.

## Supported Devices

- `fi` - Desktop (client)
- `li` - Laptop (client)  
- `si` - Server

## Supported Software

Readmes are available in `/docs/{topic}.md`

- [`bottom`](https://github.com/ClementTsang/bottom)
- `claude`
- [`direnv`](https://direnv.net/)
- [`dunst`](https://github.com/dunst-project/dunst)
- [`fish`](https://fishshell.com/)
  - [`fisher`](https://github.com/jorgebucaran/fisher) - Plugin manager with automatic updates
- `gtk`
- [Hypr](https://wiki.hypr.land/)
  - `hyprland`
  - `hypridle`
  - `hyprlock`
  - `hyperpaper`
  - `hyprfloat`
  - `hyprpicker`
  - `hyprvoice`
- [`kitty`](https://sw.kovidgoyal.net/kitty/)
- [`lazygit`](https://github.com/jesseduffield/lazygit)
- [`micro`](https://micro-editor.github.io/)
- [`mullvad`](https://mullvad.net/)
- [`python`](https://www.python.org/)
- [`solaar`](https://github.com/pwr-Solaar/Solaar)
- `systemd`
- [`waybar`](https://github.com/Alexays/Waybar)
- [`zapzap`](https://github.com/rafatosta/zapzap)
- [`zed`](https://zed.dev/)

## Installation on New Machine

A beginning is the time for taking the most delicate care that the balances are correct. 

1. **First we name her**
```bash
`hostnamectl set-hostname "NAME"``
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
sudo dnf install kitty fish curl git chezmoi
```

4. **Pull in dotfiles**
```bash
# Initialize and apply dotfiles in one step
chezmoi init --apply tijptjik
```

## Usage

Before making any changes, it is recommended to pull the latest version of the dotfiles to avoid conflicts.

### Updating

1. **Pull latest changes:**
```bash
chezmoi update
```

2. **Apply changes:**
```bash
chezmoi apply
```

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

### Packages Not Backed Up
- .zen/
- .config/BraveSoftware
- .config/Steam
- .config/uv
- .config/zed
- .local/share/firefoxpwa
