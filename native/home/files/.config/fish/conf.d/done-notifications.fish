# Identify command reports as Fish so Notjik draws a random fish for each one.
# Keep remote terminal delivery and explicitly configured notification commands.
if not set -q SSH_CLIENT; and not set -q SSH_TTY; and command -q notify-send
    set -q __done_notification_command; or set -g __done_notification_command '__fish_done_notify "$title" "$message" "$exit_status"'
end
