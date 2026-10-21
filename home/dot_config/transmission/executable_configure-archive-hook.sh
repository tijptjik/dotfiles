#!/bin/sh
# Unpackerr handles Sonarr archives after completion. Disable the old hook
# to avoid extraction races. LinuxServer runs this before transmission-daemon.

set -eu

settings_file=${TRANSMISSION_SETTINGS_FILE:-/config/settings.json}
download_dir=${TRANSMISSION_DOWNLOAD_DIR:-/data/meta/downloads}

if [ ! -f "$settings_file" ]; then
    printf '%s ERROR: settings file does not exist: %s\n' '[configure-archive-hook]' "$settings_file" >&2
    exit 1
fi

# Capture jq's output before truncating the original file. Writing back to the
# existing inode preserves the ownership and mode expected by Transmission.
updated_settings=$(jq --arg download_dir "$download_dir" '
    .["script-torrent-done-enabled"] = false
    | .["script-torrent-done-filename"] = ""
    | .["script-torrent-done-seeding-enabled"] = false
    | .["download-dir"] = $download_dir
    | .["incomplete-dir"] = $download_dir
' "$settings_file")

printf '%s\n' "$updated_settings" > "$settings_file"
printf '%s Archive extraction delegated to Unpackerr\n' '[configure-archive-hook]'
printf '%s Set download directory to %s\n' '[configure-archive-hook]' "$download_dir"
