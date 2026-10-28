# Follow-up instruction: Cloudflare Restic backup route

Implementation was authorized on 25 October 2026. See
[Cloudflare backups on Fi](cloudflare-backups.md) for the current setup,
verification evidence, and recovery procedure. The accepted design and
completion requirements below remain applicable.

## Accepted design

- Store the Restic repository under `BACKUP/cloudflare-restic` on the secondary 1 TB drive identified by filesystem UUID `E84A8D8F4A8D5B68`.
- Guard every read and write by confirming that exact UUID is mounted at the intended path. A missing mount must fail closed; it must never create or write a same-named directory on the root filesystem or another volume.
- Run backups weekly and retain `--keep-weekly 1 --keep-monthly 1` (at most two snapshots under the selected Restic retention policy).
- Encrypt the Restic repository and keep its password/recovery material out of Git, logs, command output, and chat. Use an already-approved secret store and document a recoverable access procedure without recording the secret.

## Work sequence

1. Read current backup policies and operational guides in `/home/io/.local/share/dotjik` and `/home/io/.local/share/systjik`. Inspect current Git status first and preserve unrelated staged, unstaged, and untracked work.
2. Identify precisely which Cloudflare configuration and data must be recoverable, how those exports can be obtained, their size/change rate, and any provider/API limits. Do not assume that “Cloudflare” means a complete account backup. Separate configuration export from secrets and from data stored in Cloudflare products.
3. Inspect the drive's current mount, UUID, available capacity, filesystem, and existing backup contents read-only. Confirm the accepted target path resolves to that UUID. The drive may be mounted read-only during earlier audits; do not remount it or write until the user has asked for implementation and current system policy supports the change.
4. Design a fail-closed, least-privilege export-and-backup workflow using repository conventions. Include explicit source scope, encrypted Restic initialization, weekly scheduling, retention, locking/concurrency behavior, logs without secrets, failure alerts or status evidence, and restore instructions. Never put credentials in Chezmoi plaintext or command-line arguments.
5. Before any first write, show the user the concrete source scope, scheduled commands/units, target UUID/path, encryption-secret handling, and expected retention effect for approval if not already explicitly authorized. Do not prune or delete existing backups as part of setup.
6. After implementation is authorized, test mount-UUID guards, dry-run/export behavior where available, one encrypted snapshot, and a restore into an isolated temporary directory. Verify recovered files and report exact scope and limits. Do not claim full Cloudflare recoverability from a successful Restic run alone.

## Deliverable

Provide a scope matrix of Cloudflare resources and export method/status, the proposed or implemented schedule and retention, target UUID/path verification, secret-recovery procedure location (never the secret), snapshot and isolated-restore evidence, and known exclusions. Keep all generated archives, manifests, and credentials outside Git unless the user separately requests a narrowly scoped documentation change.
