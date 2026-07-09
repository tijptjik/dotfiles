#!/usr/bin/env fish

set -l torrent_dir "$TR_TORRENT_DIR"
set -l torrent_name "$TR_TORRENT_NAME"

if test -z "$torrent_dir"
    echo "TR_TORRENT_DIR is not set"
    exit 1
end

set -l target_root "$torrent_dir"
if test -n "$torrent_name" -a -d "$torrent_dir/$torrent_name"
    set target_root "$torrent_dir/$torrent_name"
end

set -l extracted 0

for rar in "$target_root"/*.rar
    if test -f "$rar"
        set extracted 1
        echo "Extracting: $rar"

        unrar x -o+ "$rar" "$target_root/"

        if test $status -eq 0
            echo "  Success; cleaning up RAR parts..."
            find "$target_root" -maxdepth 1 -type f \( -name "*.rar" -o -name "*.r[0-9][0-9]" -o -name "*.r[1-9][0-9][0-9]" \) -delete
            echo "  Cleaned up"
        else
            echo "  Failed; keeping files"
            exit 1
        end
    end
end

if test $extracted -eq 0
    echo "No RAR files found in $target_root"
end

echo "Done."
