# Automated Chezmoi Management

This setup automates the management of your dotfiles through cron jobs with systemd journal logging.
All scripts are written in Fish shell and can be called both interactively and from cron.

## Scripts

1. **chezmoi-add** (`~/.local/bin/chezmoi-add`)
   - Runs daily at 9:00 PM
   - Adds all managed files to chezmoi repository
   - Logs to journal with tag `chezmoi-add`
   - Written in Fish shell

2. **chezmoi-update** (`~/.local/bin/chezmoi-update`)
   - Runs weekly on Sundays at 10:00 PM
   - Pulls latest changes from git
   - Applies files without local modifications
   - Reports files with local changes
   - Logs to journal with tag `chezmoi-update`
   - Written in Fish shell

3. **fisher-manage** (`~/.local/bin/fisher-manage`)
   - Runs monthly on the 1st at 10:30 PM
   - Installs Fisher if not present
   - Updates plugins (simplified - no internal update interval tracking)
   - Logs to journal with tag `fisher-manage`
   - Written in Fish shell

## Installation

Run the install script to set up the cron entries:

```bash
~/.local/bin/cron-install
```

## Viewing Logs

All scripts use `systemd-cat` for logging. View logs with:

```bash
# Daily chezmoi adds
journalctl -t chezmoi-add

# Weekly chezmoi updates
journalctl -t chezmoi-update

# Bi-weekly Fisher updates
journalctl -t fisher-manage

# View logs from today
journalctl --since today -t chezmoi-add -t chezmoi-update -t fisher-manage

# Follow logs in real-time
journalctl -f -t chezmoi-add -t chezmoi-update -t fisher-manage
```

## Managing Cron

- View current crontab: `crontab -l`
- Edit crontab: `crontab -e`
- Remove all cron jobs: `crontab -r`

## Schedule

- **Daily (9:00 PM)**: Add changed files to chezmoi
- **Weekly (Sunday 10:00 PM)**: Update chezmoi from git
- **Monthly (1st at 10:30 PM)**: Update Fisher plugins
