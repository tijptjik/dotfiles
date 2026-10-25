# Cloudflare backups on Fi

## Activation status

Setup is authorized. On 25 October 2026 the correct disk was writable, with
495 GiB free. The managed executable, credential file, and user units were
installed, and the persistent mount was added to Chezetc and Fi's `/etc/fstab`.
The export rehearsal identified a credential blocker: the existing Bitwarden
`CLOUDFLARE_API_TOKEN` can list zones and read zone settings and KV namespaces,
but DNS-record reads return HTTP 403 / Cloudflare code 10000.

The weekly timer remains disabled until the first snapshot and an isolated
restore have succeeded. No backup or restore is yet claimed by this setup.

## Scope

The approved account is `a6eeace4b6d9f8e07ab307964e74d801` (`tijptjik`).

| Content | Export | Current evidence |
| --- | --- | --- |
| Zones, DNS records, zone settings | Cloudflare API JSON, filtered to this account | 11 zones visible; DNS permission blocked |
| Workers KV | Namespace/key manifests, metadata, expiry, raw values named by SHA-256 | Independent export passed: 2 namespaces, 1 key |
| R2 | Inventory plus object bodies/names/timestamps through a read-only rclone mount | 38,464 objects, 20,409,698,437 bytes in the preflight inventory |

This is not a complete Cloudflare account backup. D1 databases, Durable Objects,
Workers deployments and secrets, Access/Tunnel configuration, and other products
are excluded. R2 custom S3 metadata is not guaranteed. Exports are collected over
time, not as a transaction across products; changing or expired objects/keys may
make a run fail. API permissions determine visibility, so scope reductions need
review. The job rejects an empty zone/namespace list and fewer than 18 R2 buckets.

## Destination and schedule

- Device UUID: `E84A8D8F4A8D5B68`, Fi's secondary 1 TB NTFS disk.
- Repository: `/run/media/io/E84A8D8F4A8D5B68/BACKUP/cloudflare-restic`.
- Chezetc manages a UUID-based, writable `nofail` mount at boot. The current
  busy drive was not remounted during setup. Reboot behavior remains untested.
- Every repository operation checks the exact mount point, UUID, writable state,
  and absence of symlink redirection. A missing disk never falls back to root.
- `cloudflare-restic-backup.timer`: Sunday 03:00 Asia/Hong_Kong, persistent
  catch-up when Fi's user manager becomes available.
- Retention: one weekly and one monthly snapshot, grouped by host/tags and
  restricted to the Cloudflare tag/host. These can select the same snapshot.
  The first successful run does not prune; later successful runs do.
- API staging files live in a private temporary directory and are removed after
  each run. R2 is mounted read-only without a VFS file cache. The job uses a
  process lock and eight Restic file readers.
- Failures are recorded in `~/.local/state/cloudflare-restic/last-failure.json`
  and the systemd journal; a critical desktop notification is attempted.
  Notifications require a working desktop session.

The Chezmoi activation hook enables the timer only when
`~/.local/state/cloudflare-restic/restore-verified.json` and the credential files
exist. Do not create that marker before completing a restore check.

## Credential recovery

No credential values belong in Git, shell arguments, logs, or documentation.

- Restic encryption: Bitwarden Secrets Manager `PRIVATE_RESTIC_PASSWORD`, secret
  ID `90f34958-6254-4b0c-bc65-b4ed0026bee2`; managed owner-only file
  `~/.config/private-storage/restic-password`. Losing it makes the repository
  unrecoverable. Access to Bitwarden must be available independently of Fi.
- API exports: currently references Bitwarden `CLOUDFLARE_API_TOKEN`, secret ID
  `c2cdd91d-02c8-4d31-83ed-b497007da128`; managed owner-only file
  `~/.config/private-storage/cloudflare-backup-token`. It needs DNS Read, Zone
  Read, Zone Settings Read, and Workers KV Storage Read for the approved scope.
  The current credential is insufficient; it must be corrected before activation.
- R2 source reads: existing `r2-tijpdata:` remote in the owner-only
  `~/.config/rclone/rclone.conf`. That credential is needed to fetch new backups,
  not to decrypt an existing Restic repository. Source credentials are not
  included in the Cloudflare snapshot.

After recovering Bitwarden access, apply only the relevant credential files with
Chezmoi; never print their rendered contents. Restore rclone configuration from
the existing device-archive recovery route or provision a replacement R2 read
credential. The R2 remote must expose all expected account buckets.

## Run and inspect

```sh
cloudflare-restic-backup --dry-run
systemctl --user start --no-block cloudflare-restic-backup.service
journalctl --user -u cloudflare-restic-backup.service -f
cat ~/.local/state/cloudflare-restic/last-success.json
systemctl --user list-timers cloudflare-restic-backup.timer
```

The dry run performs live API exports and R2 listings but does not initialize,
write, or prune the repository. A real success receipt includes the snapshot ID,
completion time, and DNS/KV/R2 counts. Restic's normal `check` validates structure;
it does not read every stored data blob.

## Isolated restore rehearsal

Before any Restic command, confirm `findmnt --mountpoint` reports the exact UUID
above, the expected path, and `rw`. Stop if anything differs or the path traverses
a symlink. Set these non-secret environment variables:

```sh
export RESTIC_REPOSITORY=/run/media/io/E84A8D8F4A8D5B68/BACKUP/cloudflare-restic
export RESTIC_PASSWORD_FILE="$HOME/.config/private-storage/restic-password"
restic snapshots --host cloudflare --tag cloudflare
```

Restore an explicit snapshot ID into a newly created owner-only directory on a
volume with enough room. Use `restic restore SNAPSHOT --target DIRECTORY --verify`.
The snapshot contains `tmp/cloudflare-restic-*/dns`, `kv`, `r2/inventory.json`, and
`r2-mount/BUCKET/OBJECT`. Never restore over a working tree or live application.

Check the restored DNS JSON counts, each KV manifest's value sizes and SHA-256
hashes, and R2 object/bucket counts. Compare representative restored R2 bodies
with fresh read-only source downloads. Record the snapshot ID, checked scope,
timestamp, and results in the private `restore-verified.json` receipt, then enable
the timer with `systemctl --user enable --now cloudflare-restic-backup.timer`.
Enabling a persistent timer may immediately run a catch-up backup.

This verifies local file recovery. Importing DNS, rehydrating KV with appropriate
expiry semantics, or uploading R2 data into a replacement account is a separate
operation requiring its own target review. Do not replay expired KV values as
permanent keys.
