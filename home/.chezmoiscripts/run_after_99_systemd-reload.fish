#!/usr/bin/env fish
#
# This script is run by chezmoi on `chezmoi apply` when this script itself changes.
# It ensures that systemd user services and timers are reloaded and enabled.

echo "Running systemd unit configuration..."

# Reload the systemd user daemon to recognize any new or changed unit files.
systemctl --user daemon-reload

# Enable and start the backup timer.
# --now ensures it starts immediately if not already active.
systemctl --user enable --now backup-packages.timer
echo "- backup-packages.timer enabled and started."

# Enable and start the hyprvoice service.
systemctl --user enable --now hyprvoice.service
echo "- hyprvoice.service enabled and started."
