# Encrypted Google Drive mount

Run `mntcrypt --set-password` in a terminal to choose the password, then
`mntcrypt` to unlock and mount encrypted Google Drive at `~/mnt/rclone/crypt`.
The mount is writable and does not start automatically at login.

Credentials are recoverable from Bitwarden Secrets Manager. The local crypt
configuration is passphrase-encrypted; decrypted configuration exists in the
user runtime directory while mounting. See [private-storage.md](private-storage.md)
for credentials, mounts, cache behavior, synchronization, and recovery.

Check upload progress with:

```sh
systemctl --user status private-mount-crypt
```

Wait for zero pending and uploading files before stopping the mount. Never
remove the VFS cache to repair a disconnected mount while writes remain pending.
