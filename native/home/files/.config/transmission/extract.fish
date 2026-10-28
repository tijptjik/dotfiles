#!/bin/sh
# Extract release archives after Transmission finishes a torrent.
#
# Transmission supplies TR_TORRENT_DIR and TR_TORRENT_NAME.  The script works
# both in the LinuxServer Transmission container and on a host installation.
# It intentionally keeps archive volumes: deleting them would make a completed
# torrent unavailable for seeding.

set -u

log() {
    printf '%s %s\n' '[extract-archives]' "$*"
}

failures=0
archives=0

extract_archive() {
    archive=$1
    destination=$2
    filename=$(basename "$archive")
    lower_filename=$(printf '%s' "$filename" | tr '[:upper:]' '[:lower:]')

    # A multipart RAR can only be extracted from its first volume.  Accept
    # both "release.rar"/"release.r00" and "release.part01.rar" layouts.
    case "$lower_filename" in
        *.part[0-9]*.rar)
            if ! printf '%s\n' "$lower_filename" | grep -Eq '\.part0*1\.rar$'; then
                return 0
            fi
            ;;
    esac

    archives=$((archives + 1))
    log "Extracting: $archive"

    case "$lower_filename" in
        *.rar)
            if ! command -v unrar >/dev/null 2>&1; then
                log "ERROR: unrar is not installed"
                failures=$((failures + 1))
                return 0
            fi
            if ! unrar x -o+ -idq "$archive" "$destination/"; then
                log "ERROR: failed to extract $archive"
                failures=$((failures + 1))
            fi
            ;;
        *.zip|*.7z|*.7z.001)
            if command -v 7z >/dev/null 2>&1; then
                seven_zip=7z
            elif command -v 7zz >/dev/null 2>&1; then
                seven_zip=7zz
            else
                log "ERROR: neither 7z nor 7zz is installed"
                failures=$((failures + 1))
                return 0
            fi
            if ! "$seven_zip" x -y -bd "-o$destination" "$archive"; then
                log "ERROR: failed to extract $archive"
                failures=$((failures + 1))
            fi
            ;;
        *.tar|*.tar.gz|*.tgz|*.tar.bz2|*.tbz|*.tbz2|*.tar.xz|*.txz)
            if ! tar -xf "$archive" -C "$destination"; then
                log "ERROR: failed to extract $archive"
                failures=$((failures + 1))
            fi
            ;;
    esac
}

torrent_dir=${TR_TORRENT_DIR:-}
torrent_name=${TR_TORRENT_NAME:-}

if [ -z "$torrent_dir" ]; then
    log 'ERROR: TR_TORRENT_DIR is not set'
    exit 2
fi

target_root=$torrent_dir
if [ -n "$torrent_name" ] && [ -d "$torrent_dir/$torrent_name" ]; then
    target_root=$torrent_dir/$torrent_name
fi

if [ ! -d "$target_root" ]; then
    log "ERROR: completed torrent directory does not exist: $target_root"
    exit 2
fi

# .zip and .7z.001 are the first volumes of their respective multipart
# formats.  For RAR, extract_archive filters out later .partNN.rar volumes.
while IFS= read -r archive; do
    extract_archive "$archive" "$target_root"
done <<EOF
$(find "$target_root" -type f \( \
    -iname '*.rar' -o \
    -iname '*.zip' -o \
    -iname '*.7z' -o \
    -iname '*.7z.001' -o \
    -iname '*.tar' -o \
    -iname '*.tar.gz' -o \
    -iname '*.tgz' -o \
    -iname '*.tar.bz2' -o \
    -iname '*.tbz' -o \
    -iname '*.tbz2' -o \
    -iname '*.tar.xz' -o \
    -iname '*.txz' \
\) -print)
EOF

if [ "$archives" -eq 0 ]; then
    log "No supported archive found in $target_root"
elif [ "$failures" -eq 0 ]; then
    log "Finished extracting $archives archive(s) in $target_root"
else
    log "ERROR: $failures of $archives archive(s) could not be extracted"
    exit 1
fi
