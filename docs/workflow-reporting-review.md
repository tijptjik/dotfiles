# Workflow reporting and service ownership

Use `tjikup --show-skips --alphabetical` for a review run. Sections buffer their
completed rows and sort by displayed application title; workers still execute
in parallel within a section. Normal runs continue streaming completion order.
Selection flags such as `--apply-dotfiles` remain combinable.

## What the rows do

- **Capture changes / Commit captured changes** captures eligible application
  settings and commits those captured paths. The commit action uses Tjikup artwork.
- **Preparation / Home prerequisites, Home scripts, System scripts** renders the
  native maintenance scripts. These are Tjikup operations, not Tjikup invocations.
- **Obsidian** in Install applications installs/checks the application.
  **Obsidian (vault checkout)** in Configuration creates/checks its external Git
  vault checkout; it does not reinstall Obsidian.
- **LLMTrim** installs the CLI/package. **Herdr (LLMTrim plugin)** installs/checks
  its Herdr integration. The historical script filename contains “remove” but its
  current implementation installs the plugin.
- **Home files** applies the base group of the native home manifest. Application
  groups already have separate configuration recipes. **System files** applies
  the host's native system manifest. These remain batch ownership/backup
  transactions, not individual application recipes. Both use Tjikup artwork.
  Breaking the remaining base/system files into smaller recipes needs explicit
  groups and dependency ownership; printing invented application rows would hide
  the current atomic preflight boundary.
- **Bitwarden (get secrets)** renders the credential manifest from the encrypted
  local cache, fetching only missing or explicitly refreshed values.
- **Synctjik (required archives)** checks the enrolled device's selected archive
  collections against restoration baselines, then sets up scheduling as needed.
  Fi had no `~/.config/synctjik/device.json` at this review, so this was a no-op;
  the status now says no archive collections are enrolled.
- **Fonts** combines legacy folder consolidation and fontconfig cache refresh in
  one recipe after native font files are applied. **Rose Punk icons** similarly
  combines icon setup and cache refresh. Both retain one result row and private
  step diagnostics.
- **Mullvad (local network access)** enables LAN access while connected to the VPN.
- **Notjik (Telegram bridge)** is the Telegram bridge service.
- **Docker** already was one recipe; its enable/start checks now report one
  combined result, “enabled and active.”

RPM package presence now reads the RPM database once per manifest check rather
than starting one `rpm -q` process per package. There is no persistent presence
cache, so installs/removals outside Tjikup remain visible on the next run.

## Desktop startup: the current managed mix

Bartjik is a user service with `PartOf=graphical-session.target`; Fish loads the
managed provider environment before executing it. Keeping the service provides
process supervision, logs, stop/restart control and graphical-session teardown.
Hyprland's startup callback also calls `systemctl --user start bartjik.service`;
that is an idempotent request for the same unit, not a second bar process.

The Hyprland startup callback currently:

- imports display/input environment into D-Bus/systemd and starts Hyprvoice;
- starts Bartjik and Hyprsunset via systemd;
- launches Fcitx, two clipboard watchers and user applications via `uwsm app`;
- applies dconf interface settings and requests Mullvad connection;
- launches Herdr, Telegram, Zapzap, Signal and configured browser/web applications.

Other user units include Notjik, its Telegram bridge, Codex LB, Collie,
Hypridle, Hyprpaper, Hyprpolkitagent and oo7. Activation hooks enable/check units;
runtime refresh hashes their definitions and inputs and restarts only changed,
active non-oneshot units. Notjik/Bartjik now have one reporting owner combining
activation and runtime refresh. The extra final blanket refresh was removed.
Backup jobs are never restarted by runtime refresh.

Recommended streamlining: retain systemd ownership for long-lived daemons and
clipboard watchers, with one ordered graphical-session environment-import step.
Keep interactive application/workspace launches in Hyprland/UWSM. This reduces
startup-order races and duplicate lifecycle logic while preserving restart
policies, logs and clean logout. This review does not change live session startup.

## Backup ownership and unit names

| Purpose | Engine | New managed unit base |
| --- | --- | --- |
| Dotfiles-like application state in R2 | Synctjik (tar/zstd, age, rclone) | `synctjik-dotfiles-lfs-backup` |
| Cloudflare DNS, KV and R2 resources | Synctjik + Restic | `synctjik-cloudflare-resources-backup` |
| Private documents/media/projects/resources backups | Synctjik + Restic | `synctjik-private-assets-backup` |
| Private assets / Google Drive synchronization | Synctjik + rclone | `synctjik-private-assets-sync` |
| Drive archives and native documents | Separate drive-restic-backup helper | Unchanged |
| Si application-backup pull and health check | Separate si-app-backup-pull helper | Unchanged |
| Screen dimming | Hyprsunset gamma 10% | `dim-screen`, displayed as Hyprsunset |

The first four have matching `.service` and `.timer` units and Synctjik artwork.
Their migration disables old timers only after checking for running jobs; a busy
job causes a needs-attention result and is left running. Standalone home apply
also checks this guard. Old managed definitions are retired by native file policy.
The new schedules retain existing credential/verified-restore activation gates.

The Drive and Si helpers are managed files/units but are not Synctjik engines.
Their names and artwork deliberately do not claim that they are. Consolidating
those implementations is a separate functional port. No timers or jobs were
restarted merely to implement this reporting review.

The dotfiles LFS job does not use Restic. Its name distinguishes the larger or
private application state from the ordinary text dotfiles kept in Git.
