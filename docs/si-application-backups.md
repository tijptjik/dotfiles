# si application-state backups

## Schedule and retention

- Server: `si-app-backup.timer`, daily at 04:00 Asia/Hong_Kong with up to five minutes jitter. Retain seven daily and four weekly snapshots (overlap means up to eleven, not necessarily eleven).
- Computer `fi`: user `si-app-backup-pull.timer`, Sundays at 06:00 Asia/Hong_Kong with up to ten minutes jitter. Copies all retained server snapshots into an independently encrypted repository, retaining seven daily and four weekly restore points as of the latest weekly transfer.
- Timers catch up after missed runs. Weekly copies retry hourly on failure and raise a desktop notification. Both computer and server must be reachable; the script tries `192.168.1.150`, then the existing `ssh.type.hk` address, verifying the host key and hostname.
- Daily 10:00 HKT check on `fi` (up to five minutes jitter): rejects server backups older than 24 hours. If no verified local copy has completed since the latest Sunday 06:00, it fetches the retained snapshots, applies retention and verifies all local repository data before recording success. A current receipt must also match a snapshot still present locally. Failed catch-up attempts notify and are attempted again at the next daily check.
- All transfers are initiated by `fi` over outbound SSH/SFTP; `fi` does not need an SSH server. Persistent timers catch missed runs when its user systemd manager starts.
- Weekly transfer cap: 2,048 KiB/s. Restic deduplicates and compresses data; snapshots are independently restorable, not a fragile chain of delta archives.

## Coverage

Current appData (including custom plugins/scripts), native Plex databases/settings, Audiobookshelf supporting metadata, MariaDB, Compose files, server dotfile source, user configuration/scripts/SSH files, `/etc`, and `/mnt/storage/public/library`.

Excluded: other media/downloads (including `public/books` and `public/library.bak`), sequencing data now in `private/wgs`, Docker layers, Flatpak packages, historical backup archives, known cache/log/artwork directories, Plex generated media/artwork, and development environments. Grimmory images are retained conservatively because some covers may be user-supplied. The exact per-source exclusion manifest is in the server backup executable and each snapshot's `backup-manifest.json`.

This is application recovery coverage, not a disk image or backup of all private documents. Private WGS files are not part of this job. The independent computer copy is geographically offsite only when that computer is elsewhere.

## Consistency and validation

Applications stay running. The job stages configuration files with rsync, then replaces every staged SQLite database with a transactionally consistent snapshot produced by SQLite's online backup API. Each database passes `PRAGMA quick_check`; Plex's bundled SQLite tool handles its custom schema if needed. Live WAL/SHM/journal files are removed only from staging after a clean database snapshot replaces them.

MariaDB is backed up with a native logical dump of all databases, routines, events and triggers. A global read lock covers non-InnoDB tables too; writes can briefly wait during the dump. Raw MariaDB database files are excluded. A failed database export or check prevents a new Restic snapshot.

Staging is root-only, on the excluded recovery-preservation directory. The backup disk UUID and all configured SnapRAID data mounts are checked before staging. SnapRAID exclusions are unchanged.

The library is backed up directly alongside staged application state, preserving
its original folder paths without making a second staging copy. Restic `--force`
rereads all source bytes on each daily backup and hashes content chunks, so the
check does not rely solely on size and modification time. Only new chunks are
stored or copied to fi; unchanged files, duplicate contents and unchanged chunks
within edited files share storage across snapshots. Existing compression and
independent encryption apply. A backup is not a monolithic archive: use `restic
ls`, `mount` or `restore` to browse and recover the directory tree. The initial
library read/transfer covers about 14.7 GiB before compression/deduplication;
later storage and network use depend on changed content. Daily full reads cost
disk I/O, but do not create daily full copies. Retention groups by host and tags
so adding this source does not create an extra independent retention group.

Restic checks repository structure after each server backup; the weekly copy reads and verifies all stored data. A successful-copy receipt is written only after verification. Server failures are logged to the system journal; weekly stale-backup detection rejects a server snapshot older than 36 hours.

## Locations and secrets

Server repository:
`/mnt/data/disk42/.recovery-preservation/app-backups/repository`

Server staging:
`/mnt/data/disk42/.recovery-preservation/app-backups/stage`

Server encryption key: `/etc/si-app-backup/password` (root-only).

Computer repository: `~/.local/share/si-app-backups/repository`.
Computer keys: `~/.config/si-app-backup/server-password` and `local-password` (owner-only). They are not committed to the dotfile repositories. Keep another secure copy of the keys in a password manager: the encrypted repositories cannot be recovered without them.

Status receipts:
- Server `/var/lib/si-app-backup/last-success.json`
- Computer `~/.local/share/si-app-backups/last-success.json`

## Check or run manually (Fish-compatible)

On the server:

```fish
sudo systemctl status si-app-backup.timer
sudo journalctl -u si-app-backup.service -n 40 --no-pager
sudo systemctl start --no-block si-app-backup.service
```

On this computer:

```fish
systemctl --user status si-app-backup-pull.timer
journalctl --user -u si-app-backup-pull.service -n 40 --no-pager
systemctl --user start --no-block si-app-backup-pull.service
restic -r ~/.local/share/si-app-backups/repository -p ~/.config/si-app-backup/local-password snapshots
```

## Restore safely

Restore to an empty temporary directory first, never directly over a live database:

```fish
sudo restic -r ~/.local/share/si-app-backups/repository -p ~/.config/si-app-backup/local-password restore latest --target /tmp/si-app-restore --verify --exclude-xattr security.selinux
```

The rehearsal excludes SELinux labels because the destination machine applies its own policy. After installing files into their real service paths, apply the appropriate labels with `restorecon`; other file contents and metadata remain in the backup.

The snapshot contains the staging tree at
`mnt/data/disk42/.recovery-preservation/app-backups/stage/`.
Within that tree are the original source paths plus a manifest. Stop the affected
service before replacing its state; preserve owner/group/modes. SQLite snapshots
are self-contained: remove stale WAL/SHM files from the restoration destination
before installing the restored database. MariaDB is restored from
`database-dumps/mariadb.sql` into a compatible MariaDB server. Restore deployment
configuration before starting dependent services. The manifest records database
checks and the services running at capture time.

Snapshots taken after library coverage was enabled also contain
`mnt/storage/public/library/` directly beneath the restore target. To restore
only the library, add `--include /mnt/storage/public/library` to the restore
command. Use a new temporary destination and check it before replacing files.
Earlier application-only snapshots do not contain the library. `library.bak`
is not included or removed automatically; the October 21 content comparison
reports are in `~/downloads/library-audit-2026-10-21/` on si.

## Managed sources

- `../chezetc/etc/si-app-backup/executable_backup.py`
- `../chezetc/etc/systemd/system/si-app-backup*`
- `home/dot_local/bin/executable_si-app-backup-pull`
- `home/dot_config/systemd/user/si-app-backup-*`
- Restic is declared in chezetc's common package list.

Initial backup, off-computer copy and restore-test results are recorded in the storage recovery log after verification.

## Initial validation (October 21, 2026)

The first accepted snapshot, `6b7af0d1`, contained 18,825 files / 3.867 GiB,
storing 1.942 GiB after deduplication and compression. Repository checks passed.
Adding configuration-decryption keys and updated scripts created snapshot
`5e86dbcd`: one new file, two changed files, 18,823 unchanged files, and only
35.515 KiB newly stored.

Forty SQLite snapshots passed checks. Prowlarr's live database has inconsistent
history indexes: the job preserves its unrepaired snapshot in
`database-evidence/prowlarr-before-reindex.db`, rebuilds indexes only in the
backup copy and requires a full integrity check. The live database has not been
modified by this repair. This source-database issue remains a follow-up item.

The MariaDB dump (17,062,031 bytes) was imported into a disposable container
using the same image and backed-up configuration, with networking disabled and
no production data mounts. Application schema/table counts matched the source,
and `mariadb-check --all-databases` passed. The temporary container and its data
were removed. Restore tooling must wait for the image's full initialization
marker before importing: its temporary bootstrap server is not ready for a
restore even when it briefly answers SQL queries.

An earlier shutdown-based prototype rejected a snapshot after Prowlarr exceeded
its shutdown timeout and restored the previous services. It was replaced with
the online database-export workflow; scheduled backups no longer stop apps.

Public SSH address `ssh.type.hk` was unreachable during setup; LAN access worked.
Initial computer-copy verification is recorded in the storage recovery log.

The independent copy subsequently completed and passed a full encrypted-pack
read check. A complete local restore passed content verification, and Radarr,
Sonarr and Prowlarr passed full SQLite integrity checks. Configuration-decryption
keys and Compose files were present. Temporary restored files were removed.
All three timers are active; the immediate freshness check passed. See
`../troubleshooting/si-2026-10-21/local-backup-restore-verification.json` and the
copy/server receipts alongside it.

## User recovery-key handoff

An owner-only document on fi, `~/.config/si-app-backup/RECOVERY-KEYS.txt`,
contains both independent repository passwords and basic recovery instructions.
Copy it into a password manager secure note accessible independently of these
computers. The document is outside version control; do not put it in public
downloads or commit it. Passwords alone are insufficient: retain the repository
files too. Full recovery steps are above.

Regular parity maintenance is described in [the SnapRAID runbook](si-snapraid-maintenance.md).
It serializes with application backups. Parity is separate from these versioned backups.

## Library validation (October 21, 2026)

Snapshot `3c1afc12` includes all 2,912 library files / 15,774,170,682 bytes,
alongside the consistent application exports. The completed job passed its
repository check. EPUB and PDF samples were restored into a private temporary
directory; their SHA-256 hashes matched the full source inventory, and temporary
restores were removed. Adding library coverage stored 15,714,143,657 packed bytes
(about 14.6 GiB) including that run's application changes. Later copies reuse
unchanged chunks. Fi's first expanded copy was started through the existing
service; its success receipt is written only after its full data check passes.

The complete SHA-256 comparison found every `library.bak` book represented in
the current library. Of 2,896 backup files, 2,876 match at the same path, one was
moved unchanged, and 19 have renamed/current versions: eight EPUB metadata-only
edits, six EPUB metadata/cover edits, and five PDFs with identical page content,
resources, geometry, annotations and extracted text. Current has 16 additional
files. This is not a byte-identical subset: old metadata/covers differ, and
timestamps alone do not prove chronology. Neither tree was changed. Full audit
reports are in `~/downloads/library-audit-2026-10-21/` on si and fi.
