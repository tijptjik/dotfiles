# Fleet storage and backup map

[![Fi, Li, Si and Google backup relationships](assets/fleet-backup-map.png)](assets/fleet-backup-map.png)

[PNG](assets/fleet-backup-map.png) · [Editable SVG](assets/fleet-backup-map.svg)

`giD` means Google Drive and `giP` means Google Photos. This page describes the
current backup scopes, schedules, and retention.

## Coverage

| Content | Working location | Backup or protection | Retention / schedule |
| --- | --- | --- | --- |
| Lowercase documents, media, projects, resources | Local Fi/Li folders, hourly bisync through giD `private/` | Encrypted per-client Restic repositories on Si (`/mnt/storage/private/backups/clients/fi` and `/mnt/storage/private/backups/clients/li`) | Fi 00:00, Li 01:00 fallback; one snapshot under 1 day, 1–3 days, 3–7 days, 7–14 days, 14–31 days, 31–92 days, and 92–365 days; then one per older calendar year |
| Selected device settings, SSH/GPG, keys and application state | Host-specific folders on Fi/Li/Si | Verified archives in Cloudflare R2; age encryption except explicit asset exceptions | Fi 00:00, Li 00:15, Si 00:30; latest only or latest + previous ISO week + previous month |
| Si applications, Plex, MariaDB, config, scripts and public/library | Si app state and library | Daily Restic on Si disk42, then independently encrypted Restic copy on Fi | Si 04:00; Fi Sunday 06:00 plus daily 10:00 check/catch-up; 7 daily + 4 weekly |
| Ephemera final image (2.0.0) | Si Docker image | Verified image export in giD `private/backups/software/ephemera/v2.0.0-37d95e68394b/`; [recovery instructions](si-application-backups.md#ephemera-final-image) | One-time preservation; indefinite retention |
| Bulk data on Si | Five data disks | Two SnapRAID parity disks; separate from versioned backup | Daily 05:00 sync; Sunday 08:00 25% scrub of eligible blocks |
| Google Photos | Google Photos (`giP`) | No independent copy configured; TODO: evaluate Immich on Si as a backup destination | Not scheduled |
| Google-native documents and Drive-only archives | giD `GSUITE/` and `private/archives/` | Encrypted Restic repository on Si at `/mnt/storage/private/backups/google-drive`; Google Docs/Sheets/Slides/Drawings are exported to compatible formats | Daily 02:00 HKT; 1 daily / 1 weekly / 1 monthly per source |
| Cloudflare DNS, KV and R2 | Cloudflare | Export and Restic backup to fiX, Fi's secondary 1 TB disk | Sunday 03:00 HKT; 1 weekly + 1 monthly |

Schedules use HKT. Persistent timers catch up when the host's user systemd
manager returns. Li's scheduled private backup skips when Fi has completed a
verified backup that day, so Li-only unsynchronized edits may miss that day's
server snapshot. Google Drive exports preserve document content, not sharing
ACLs, comments, revision history, or native editing semantics. Google Photos
has no independent copy; evaluating Immich on Si is a TODO.

## Source references

- [Private storage](private-storage.md) and the managed `private-storage` tool.
- [Dotfiles LFS](device-archives.md) and `native/home/files/.config/archive-policy.json`.
  The JSON policy is authoritative for current per-folder assignments.
- [Si application backups](si-application-backups.md) and the server backup script.
- [SnapRAID maintenance](si-snapraid-maintenance.md).
- [Email archive format](email-archive.md).
- [Cloudflare backups](cloudflare-backups.md), `native/home/files/.local/bin/cloudflare-restic-backup`, and its user timer.
- Related Tjikup source: `etc/si-app-backup/`, `tjikup system update-apps`,
  `../native/tasks/system/run_after_95-si-app-updates.fish.tmpl`.
