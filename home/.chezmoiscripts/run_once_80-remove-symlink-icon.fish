#!/usr/bin/env fish

echo "[CONFIG] Symbolic Link Icon..."
# Use find to avoid an error if the glob doesn't match any files.
sudo find /usr/share/icons -name "emblem-symbolic-link.png" -delete
