# Encrypted Google Drive

On fi, `rclone-crypt.service` mounts `crypt:` writable at `~/mnt/rclone/crypt`.
It uses `~/.local/state/storage-review/legacy-rclone.conf` (mode 0600), whose
`crypt` remote wraps `type-drive:crypt`. Credentials and encryption secrets stay
outside Git. Preserve this configuration securely for recovery.

The user service starts at login and restarts after failure. It retains rclone's
VFS write cache; do not delete that cache when repairing a mount. Other review
mounts are still temporary, read-only mounts.

Inspect with `systemctl --user status rclone-crypt` and
`journalctl --user -u rclone-crypt`. A disconnected FUSE endpoint with no rclone
process is a stale mount. Stop the service, unmount with
`fusermount3 -u ~/mnt/rclone/crypt`, then start the service. OAuth failures require
`rclone --config ~/.local/state/storage-review/legacy-rclone.conf config reconnect type-drive:`.
