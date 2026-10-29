# Synctjik protection cutover

Implementation sources now use native Synctjik for Drive, application backup,
independent copy/health, staged restoration, and SnapRAID maintenance/alerts.
Credentials, repository formats, receipt paths, unit names and timer calendars
are unchanged. Policy is in the native JSON files; Python under system/tests/legacy
is a frozen test oracle only. No live deployment or backup acceptance is implied.

Release publication and pin changes remain deferred. Before applying changed
units, install a reviewed binary reporting `"protection_backends": 1` at
`~/.local/bin/synctjik` and, on Si, `/usr/local/bin/synctjik`. System services use
the root-owned binary because notification services protect home directories.
Never point a root service at a user-writable executable. Do not apply these unit
changes with an older binary. Preserve the old executable until its jobs finish.

Use `synctjik protection-migration --policy POLICY -- COMMAND...` for the reviewed
file cutover: it takes the existing locks, checks workers, and holds the locks
through COMMAND. Busy workers return 75. No worker is stopped or restarted and
no timer is enabled. Tjikup workflow and standalone file selection invoke the native guard for both
home and system apply when a checkout migration policy is present. The shared
interface is `apps/tjikup/src/workflow_files/protection.rs`; it delegates all
protection policy and lock handling to Synctjik. `scripts/protection-cutover.sh`
is also available for an explicitly prepared direct file-apply command.
For a manually reviewed system manifest apply, run the same guard as root with
`native/protection-migration/system-si.json` and the prepared `tjikup files apply`
command; prepare private rendered inputs as the invoking user first. Ordinary
system configuration/decryption remains owned by Tjikup. Do not run a root
`workflow files system` using another user's home/environment.

The declared manager reload runs inside the native guard after successful file
apply and before releasing locks. It does not start services or enable timers.
Then inspect
`systemctl cat` and `show -p ExecStart,ExecStopPost` for the affected units. Keep
existing timer enablement; do not enable schedules as a validation side effect.
An active old process must finish against its pinned runtime before switching.
Check manual workers via the same lock guard, not just systemd exit status.

New commands accept `--policy`: `drive backup|snapshots|restore`,
`app-backup backup`, `app-pull copy|health`, `app-restore stage|verify|install|import-mariadb`,
`snapraid guard|status|preflight|sync|scrub|resume`, and
`snapraid-notify failure|recovery|health`. Check subcommand help first.
`drive restore` and `app-restore stage` require an exact full snapshot ID and a
new destination. File installation requires all destinations empty and all
writers explicitly stopped. A started MariaDB import receipt blocks retries
until manual diagnosis. Legacy command aliases delegate only to Synctjik.

Validation must use generated data and fake commands; never invoke actual sync,
scrub, alerts, or private restores as a test. Live installed routing, real backup
completion, and a restored-content/hash rehearsal are separate deployment gates.
