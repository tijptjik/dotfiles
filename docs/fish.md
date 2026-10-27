# Fish

## Setup

### Fish Shell Configuration
- **Main config**: `~/.config/fish/config.fish`
- **Environment**: `~/.config/fish/conf.d/variables.fish`
- **Secrets**: `~/.config/fish/conf.d/secrets.fish`
- **Aliases**: `~/.config/fish/conf.d/aliases.fish`
- **Utilities**: `~/.config/fish/conf.d/utils.fish`
- **Plugins**: `~/.config/fish/fish_plugins`
- **Update Script**: `~/.local/bin/fisher-update`

### Command Notifications

The `done` plugin sends local command completion notifications as `fish`, including
inside Kitty. Notjik chooses a random image from its 28-fish collection for each
new notification and keeps that fish when the notification is updated or viewed
in history. Failure urgency, notification duration, sound, focus checks, and the
Tjikup exclusions still follow `done`'s settings.

`conf.d/done-notifications.fish` enables this when `notify-send` is available.
SSH sessions retain terminal delivery, and an explicitly configured
`__done_notification_command` is preserved. New shells load this automatically;
in existing shells, run `source ~/.config/fish/conf.d/done-notifications.fish`.

### Fisher Plugin Management
- **Automatic installation**: Fisher installs itself on first shell startup
- **Plugin manifest**: All plugins from `fish_plugins` are automatically installed
- **Background execution**: Updates run silently without slowing shell startup
- **Schedule**: Runs on shell startup, updates every 14 days

## Post-Installation

### 1. Set Fish as Default Shell

```bash
# Add fish to /etc/shells if not present
echo $(which fish) | sudo tee -a /etc/shells

# Set fish as default shell
chsh -s $(which fish)
```

### 2. Verify Fisher Installation

```bash
# Start a new fish shell
fish

# Check Fisher status
fisher list

# Verify plugins are installed
fisher update  # Should be up-to-date
```

### 3. Test Automatic Updates

```bash
# Run the Fisher management script manually
~/.local/bin/fisher-update
```


### Managing Fisher Plugins

- **Add new plugin**: Edit `~/.config/fish/fish_plugins` and run `fisher update`
- **Remove plugin**: Edit `~/.config/fish/fish_plugins` and run `fisher update`
- **List plugins**: `fisher list`
- **Force update**: `fisher update`
