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

# hyprpolkitagent
systemctl --user enable --now hyprpolkitagent.service
echo "- hyprpolkitagent.service enabled and started."

# hypridle
systemctl --user enable --now hypridle.service
echo "- hypridle.service enabled and started."

# hyprsunset
systemctl --user enable --now hyprsunset.service
echo "- hyprsunset.service enabled and started."

# hyprpaper
systemctl --user enable --now hyprpaper.service
echo "- hyprpaper.service enabled and started."

# hyprfloat
systemctl --user enable --now hyprfloat.service
echo "- hyprfloat.service enabled and started."

# hyprvoice
systemctl --user enable --now hyprvoice.service
echo "- hyprvoice.service enabled and started."
