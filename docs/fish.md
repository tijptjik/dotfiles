# Fish

## Setup

### Fish Shell Configuration
- **Main config**: `~/.config/fish/config.fish`
- **Environment**: `~/.config/fish/conf.d/export.fish`
- **Secrets**: `~/.config/fish/conf.d/secrets.fish`
- **Aliases**: `~/.config/fish/conf.d/aliases.fish`
- **Utilities**: `~/.config/fish/conf.d/utils.fish`
- **Plugins**: `~/.config/fish/fish_plugins`
- **Update Script**: `~/.local/bin/fisher-manage`

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
~/.local/bin/fisher-manage
```


### Managing Fisher Plugins

- **Add new plugin**: Edit `~/.config/fish/fish_plugins` and run `fisher update`
- **Remove plugin**: Edit `~/.config/fish/fish_plugins` and run `fisher update`
- **List plugins**: `fisher list`
- **Force update**: `fisher update`
