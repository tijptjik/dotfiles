# Cloudflare backups on Fi

Fi backs up selected Cloudflare data to an encrypted Restic repository on its
secondary 1 TB disk. The weekly user timer runs Sunday at 03:00 HKT and retains
one weekly and one monthly snapshot. The backup is separate from the Si
application copy.

## Scope

- DNS records and zone settings for the configured account.
- Workers KV namespaces, key metadata, expiry and values.
- R2 bucket inventories and object contents through a read-only rclone mount.

D1 databases, Durable Objects, Workers deployments and secrets,
Access/Tunnel configuration, and other Cloudflare products are not included.
R2 custom S3 metadata is not guaranteed. Exports happen over time, not as one
transaction across Cloudflare products.

## Storage and protection

- Destination: Fi's secondary disk, UUID `E84A8D8F4A8D5B68`.
- Repository: `/run/media/io/E84A8D8F4A8D5B68/BACKUP/cloudflare-restic`.
- Chezetc mounts the disk by UUID at boot. Each backup checks the mount point,
  UUID and writable state; a missing disk does not fall back to the system disk.
- Restic encrypts and deduplicates snapshots. The API token is provisioned from
  Bitwarden. Staging files and the read-only R2 mount are temporary.
- A successful run checks the repository and prunes to one weekly and one
  monthly snapshot. The first successful run does not prune.

The service retries one incomplete-source read by refreshing the exports and
R2 mount. Other errors stop the run. Incomplete runs do not create success
receipts or prune snapshots. Failures go to the systemd journal and
`~/.local/state/cloudflare-restic/last-failure.json`.

## Operations

Check the weekly timer and recent run:

```sh
systemctl --user status cloudflare-restic-backup.timer
journalctl --user -u cloudflare-restic-backup.service
```

Success receipts are under `~/.local/state/cloudflare-restic/`. The initial
isolated restore check is complete; repeat restore rehearsals periodically.
Restic recovery verifies the backed-up files. Recreating Cloudflare services
from those files is a separate recovery procedure.

After a reboot, confirm that the UUID disk is mounted at the repository path
before the next scheduled run. Fi is offsite only while physically located
elsewhere.
