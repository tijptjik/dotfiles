# Shared video permissions on si

The media services use UID 1000 and media GID 950. Recovered root-owned mode
0600 files and root-owned mode 0755 movie/season directories prevented reads and
imports despite correct downloader credentials and mounts.

This policy maintains group 950 read/write access to regular files, group
read/write/traverse access to directories, and directory setgid inheritance.
It preserves owners and existing owner/other permission bits, adds no executable
bits to files, and does not write file contents or timestamps.

Scope is exactly `public/movies`, `public/shows`, `meta/downloads/radarr`, and
`meta/downloads/sonarr` on the five verified array data mounts. App configuration,
private storage, other media categories, parity and recovery evidence are outside
the scope. Symlinks are not followed, and unexpected nested filesystems fail.
Every required root and disk UUID is checked before changing any permissions.

The service runs before Docker starts and every 15 minutes afterward. It shares
the parity/backup locks and defers a busy run; it never stops or restarts apps.
Changes are journalled before mutation in root-only JSONL under
`/var/lib/si-media-permissions`. Each record retains device/inode, original
owner/group/mode, size, mtime and existing ACL attributes for reviewed rollback.
Check identity before using a journal: imports can move or replace files later.

```sh
sudo /usr/local/lib/tjikup/tjikup system permissions       # audit only
sudo /usr/local/lib/tjikup/tjikup system permissions --apply
sudo systemctl status si-media-permissions.timer
sudo cat /var/lib/si-media-permissions/last-success.json
```

The managed Compose environment sets `UMASK=002` for Sonarr, Radarr and
Transmission. Transmission's init hook also sets its application umask to 2.
Unpackerr extracts files as 0664 and directories as 0775. Existing parent setgid
directories supply group inheritance. Sonarr/Radarr native permission rewriting
is disabled: the filesystem policy and creation masks own that responsibility.
Those native settings are retained in the encrypted application backups.

The provisioning directory manifest supplies the same group and setgid modes
for new movie, TV and Arr download roots. Ordinary directory provisioning still
preserves existing directories; the separately guarded policy performs repairs.
Fi/li ignore all policy files/units, and the enable hook renders only on servers.
