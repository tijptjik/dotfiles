#!/bin/sh
# Keep the Transmission container's runtime-managed settings pointed at the
# archive extraction hook. LinuxServer runs this before transmission-daemon.

set -eu

settings_file=${TRANSMISSION_SETTINGS_FILE:-/config/settings.json}
hook_path=${TRANSMISSION_ARCHIVE_HOOK:-/usr/local/bin/extract-sonarr-archives}

if [ ! -f "$settings_file" ]; then
    printf '%s ERROR: settings file does not exist: %s\n' '[configure-archive-hook]' "$settings_file" >&2
    exit 1
fi

if [ ! -x "$hook_path" ]; then
    printf '%s ERROR: extraction hook is not executable: %s\n' '[configure-archive-hook]' "$hook_path" >&2
    exit 1
fi

# Capture jq's output before truncating the original file. Writing back to the
# existing inode preserves the ownership and mode expected by Transmission.
updated_settings=$(jq --arg hook_path "$hook_path" '
    .["script-torrent-done-enabled"] = true
    | .["script-torrent-done-filename"] = $hook_path
    | .["script-torrent-done-seeding-enabled"] = false
' "$settings_file")

printf '%s\n' "$updated_settings" > "$settings_file"
printf '%s Enabled archive extraction via %s\n' '[configure-archive-hook]' "$hook_path"
