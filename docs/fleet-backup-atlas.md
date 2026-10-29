# Fleet storage atlas

[![Devices, content and recovery relationships](assets/fleet-backup-atlas.png)](assets/fleet-backup-atlas.png)

[Full-resolution PNG](assets/fleet-backup-atlas.png) ·
[Editable SVG](assets/fleet-backup-atlas.svg) ·
[Backup map](fleet-backup-map.md)

## Backup locations

The atlas shows the configured backup routes and their current schedules.
Schedules use HKT. Timer jobs run under each host's user systemd manager.

## Location icons

| ID | Location | Meaning in this setup |
| --- | --- | --- |
| `fi` | Desktop | Local working folders; independent Si application repository on the main/home filesystem |
| `fiX` | Secondary desktop SSD | Cloudflare Restic repository; distinct from Fi's server-application copy |
| `li` | Laptop | Local working folders; private-backup fallback when Fi has not succeeded that day |
| `si` | Server | Applications, storage and recovery jobs |
| `siS` | Server storage pool | Five mergerfs data disks; private client repositories and public collections |
| `siP` | Server parity | Two SnapRAID parity disks; configured scope only |
| `gi` | Google | Parent provider grouping, not shorthand for a second machine or Drive |
| `giD` | Google Drive | `type-drive:`; synchronized private files, cloud-only archives and Google-native documents |
| `giP` | Google Photos | Provider-hosted personal photos; TODO: evaluate Immich on Si as a backup destination |
| `cf` / `cfR2` | Cloudflare / R2 | DNS/KV exports and object storage, including Dotfiles LFS and public assets |
| `git` | Git remotes | Committed code and configuration history |
| `bw` | Bitwarden | Hosted vault and selected Secrets Manager provisioning; independently recoverable vault access is required |

The server's application repository is at
`/mnt/data/disk42/.recovery-preservation/app-backups/repository`. It is a recovery
area on a data disk, excluded from parity; the diagram does not depict an extra
physical disk. The independent copy lives at
`fi:~/.local/share/si-app-backups/repository`, **not on `fiX`**.

## Content icons and coverage

Content tags are deliberately nonexclusive. **Archive** describes inactive,
themed material; **backup** describes a recovery copy. Mail, photos, secrets or
code can also be archived or backed up. A folder named `backups` does not establish
a recurring job or a successful restore.

| Type | Meaning / location | Protection boundary |
| --- | --- | --- |
| Archives | Themed inactive collections; e.g. `giD:private/archives/` | Daily encrypted Restic backup on Si |
| Backups | Phone exports, OS/partition images, DB dumps, snapshots | The recurring Restic routes below are defined; no blanket phone/OS image job is implied |
| Code | Git-backed repos on workstations and remotes | Git protects pushed commits; `~/code`, uncommitted/untracked files and repository secrets are outside the four-folder private backup |
| Personal artefacts | Fi/Li `~/documents`, `~/media`, `~/projects`, `~/resources` | Hourly Drive bisync plus client Restic snapshots on Si; uppercase `~/Documents` is outside this job |
| Downloads | Pre-organized staging / downloads | Deliberately excluded from backup and Si parity |
| Media | Si movies, shows, books and audiobooks | Configured bulk parity; most public media excluded from application Restic. Only `public/library` has the documented library backup, not `public/books` or `library.bak` |
| Photos | Personal images in local folders and/or Google Photos | Local images inherit their folder's protection; Google Photos has no configured independent copy. TODO: evaluate Immich on Si |
| Assets | Public image and dataset releases, including R2 objects | Cloudflare R2 is included in the Fi Restic backup scope |
| Configs | Git-managed dotfiles, scripts, templates, Compose and system configuration | Git history + Tjikup/Tjikup deployment; selected live state also in device/app backups |
| Secrets | Keys, credentials, encryption/recovery material | Bitwarden provisioning and selected age-encrypted Dotfiles LFS backups; never committed to Git |
| **Mail** | Messages, attachments, indexes and reader exports | Encrypted structured archives under `giD:private/archives/mail/structured/`; included in the Si Drive backup |
| **App state / databases** | Mutable application data, SQLite/Plex, MariaDB | Application-consistent exports → Si Restic → independently encrypted Fi repository |
| **Recovery software** | Ephemera 2.0.0 final Docker image | Verified permanent export in `giD:private/backups/software/ephemera/v2.0.0-37d95e68394b/`; superseded Si tar removed. [Recovery instructions](si-application-backups.md#ephemera-final-image) |
| **Cloud-native documents** | Google Docs, Sheets, Slides and Drawings in `GSUITE/` | Daily Si Restic export and backup at 02:00 HKT; 1 daily / 1 weekly / 1 monthly per source. Sharing, comments and revision history are not retained |
## Implemented schedule summary

All times HKT; persistent timers may catch up and some runs include jitter.

- **Personal:** Fi Drive sync at :05 and Li at :35 hourly. Fi Restic at 00:00;
  Li 01:00 fallback. Each client repository keeps one snapshot in each band:
  under 1 day, 1–3 days, 3–7 days, 7–14 days, 14–31 days, 31–92 days, and
  92–365 days; then one per older calendar year. Li-only unsynchronized edits
  can remain unprotected when its fallback skips. The repositories are
  `/mnt/storage/private/backups/clients/fi` and
  `/mnt/storage/private/backups/clients/li` on Si. The Si-to-Fi app
  repository is separate from these client repositories and does not include
  them. No independent replica of their snapshot history is configured outside
  Si; Drive synchronization is not a replica of that history.
- **Server apps:** Si 04:00, 7 daily / 4 weekly. Fi Restic copy Sunday 06:00,
  daily 10:00 freshness/catch-up. Fi is geographically offsite only when elsewhere.
- **Dotfiles LFS:** Fi 00:00, Li 00:15, Si 00:30. Selected per-host folders;
  latest only, or latest + previous week + previous month according to policy.
- **Google Drive archives and native documents:** Si daily backup at 02:00;
  1 daily / 1 weekly / 1 monthly snapshot per source.
- **Cloudflare:** Fi backup at 03:00 Sunday; 1 weekly / 1 monthly after the
  initial backup and isolated restore. Scope is DNS/settings, KV and R2.
- **Parity:** daily 05:00 sync; Sunday 08:00 scrub of 25% of eligible blocks.
  Excludes `meta/`, downloads and `.recovery-preservation/`.

## Sources and editing

- [Backup map](fleet-backup-map.md)
- [Private storage](private-storage.md)
- [Dotfiles LFS policy](device-archives.md)
- [Si app recovery](si-application-backups.md)
- [SnapRAID maintenance](si-snapraid-maintenance.md)
- [Cloudflare backups](cloudflare-backups.md)
- [Mail archive format](email-archive.md)

The SVG uses original line icons and editable text, with no remote assets.
Rebuild with `python3 scripts/render_fleet_backup_atlas.py`; add `--png` when
CairoSVG is available.
