# Si application updates

`tjikup` runs the Si-only `run_after_95-si-app-updates.fish` hook through Chezetc.
A direct `chezetc apply` also runs it. Clients do not run this hook.
The `run_after_` phase installs `/etc/si-provision/update_apps.py` and the other
managed files before invoking the updater, including on the first apply.

## Plex

Plex is the native `plexmediaserver` RPM service, not a Compose container.
Routine DNF updates exclude this RPM; reconciliation also excludes it when
already installed. A fresh installation remains part of server provisioning.
The app updater reads the local Plex token from `Preferences.xml` in memory
and requests `http://127.0.0.1:32400/status/sessions`. Tokens and session details
are never printed or written to update records.

Any reported session, including paused playback, defers the Plex update. A
missing token, API error, timeout, or malformed response also defers it. When
idle, the updater checks for a newer RPM, downloads it, and checks sessions
again immediately before the cached RPM transaction. This minimizes the gap;
it cannot prevent a new viewer connecting after the final check. It does not
block new sessions, stop Plex manually, or terminate viewers. Manual DNF
commands and explicitly requested Fedora release upgrades are outside this guard.

## Docker

The updater targets `/home/m/dockers/docker-compose.yaml` and only services
already running in that Compose project. It pulls their configured image tags
and rebuilds local build services (currently Lidarr) with `--pull`. Up to three
image preparation jobs run concurrently, and status rows appear as each finishes.
Container recreation starts only after preparation finishes and stays sequential.
Digest-pinned images remain pinned. Ephemera is a frozen final release: its running container
is retained and the updater never pulls, builds, or recreates it. A failed pull/build leaves the current
container in place and reports a warning. There is no automatic image pruning.

Successful update rows show `service (old version)` and the new version, as RPM
updates do. Image versions come from OCI/label-schema metadata or LinuxServer
build labels. Missing or unchanged version labels fall back to short image IDs,
so rebuilt images remain distinguishable. Plex also reports old/new RPM versions.

Only services whose image ID changed are recreated. The chosen image IDs are
pinned in a temporary Compose override for the update, and services are updated
one at a time using `up --no-deps --no-build --pull never --wait`. Dependencies
and intentionally stopped services are not started or recreated implicitly.
Docker health checks (where configured), running state, and image IDs are checked;
this is not an end-to-end application acceptance check. On a recreation failure,
further container recreation stops for operator review. Databases may have
migrated, so there is no automatic rollback to an older image.

## Backup and concurrency

Updates require a successful application-backup receipt from the last 24 hours.
If it is missing or older, the updater requests `si-app-backup.service`
asynchronously and defers changes; rerun `tjikup` after backup succeeds.
This uses the existing daily 04:00 backup rather than running a full backup on
every no-change update. The receipt is a recovery point, not a zero-data-loss
rollback guarantee.

The updater shares `/run/lock/si-app-backup.lock` with backup/restore and skips
while that lock is held. A separate update lock prevents overlapping updater
runs. Individual commands and the overall update pass are time-bounded; a
budget exhaustion defers remaining work. No full stack shutdown is used.

Root-only update records live under `/var/lib/si-app-updates/<UTC timestamp>/`:
`containers-before.json` records previous image/container IDs, `images.json`
records selected new images, and failure logs retain command diagnostics.
Compose environment variables and Plex credentials are not included in the
image records. Keep old images and a compatible backup when planning rollback.
