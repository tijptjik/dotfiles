# Rebuilding si: configuration audit and provisioning baseline

Audit date: 2026-10-21. **Implementation follow-up: see [SERVER-BOOTSTRAP.md](SERVER-BOOTSTRAP.md) for the implemented tools, routine-update protections and current commands. The audit below records the initial baseline; its outstanding items are superseded where implemented in that guide.** This is a recovery-oriented baseline, **not yet a tested unattended installer**. The Dotjik checkout contains system configuration; applying it and restoring application state are separate operations. The current server has not been broadly reapplied or restarted by this audit.

## Ownership of configuration

Keep `/etc` policy in **systjik**, home-owned Compose/build definitions in **dotjik**, and live databases plus credentials in the consistent application backups. Tjikup orchestrates configuration and Synctjik owns restoration; Compose policy remains in Dotjik.

| Component | Version-controlled source / action | Restore or remaining work |
| --- | --- | --- |
| Disk identities and roles | `native/si/files/si-snapraid-maintenance/config.json` is the storage inventory; `tjikup system storage` derives array fstab entries | Reattach those disks; a replacement array needs an explicitly reviewed new inventory. Never format automatically. |
| OS mounts | Keep installer-owned root, home, boot and EFI entries | Server fstab target is ignored; explicitly run the selective storage helper after review. |
| SnapRAID | `native/si/files/snapraid.conf.j2`, maintenance script, guards and units | Preserve content/parity files. Template now matches disk42 and new parity1 and excludes `/docker/` and `/.recovery-preservation/`. Keep template layout in agreement with the inventory. |
| mergerfs | Explicit branches in generated fstab, mounts required before services | Installed 2.32.6 fc33 package has no candidate in current repositories. Select a supported, pinned, checksum-verified upstream package and test its mount options before automating installation. Do not silently upgrade the live pool. |
| Docker and Compose | Package/repo declarations, `etc/docker/daemon.json`, systemd mount guard; dotjik `native/home/files/dockers/docker-compose.yaml.j2` | Docker data-root is `/mnt/data/disk22/docker`. Images retain their intended tags; pin only when explicitly chosen in Compose. Use a deliberate update workflow. Do not restore Docker layers as application backups. |
| Sonarr, Radarr, Prowlarr, Lidarr, Bookshelf | Compose; Lidarr ffmpeg Dockerfile | Restore appData databases/config: paths, profiles, indexes, clients, tokens, notifications and monitoring state live there. Future API reconciliation must preserve existing user settings. |
| Byparr, FlareSolverr | Compose | Audit FlareSolverr anonymous `/config` volume before treating it as disposable. |
| LazyLibrarian, Ephemera, Shelfmark, Octo-fiestarr, Grimmory | Compose | Restore appData, credentials and dependencies; verify service-specific health after restore. |
| Audiobookshelf | Compose | Restore appData and persistent `meta/appCache/audiobookshelf`; catalog and progress are not rebuildable assets. |
| Navidrome, Feishin, Tautulli, Plex Rewind | Compose | Restore appData databases/config and Plex integration credentials. |
| Plex (native) | Package/repository, existing systemd override runs as media | Restore `meta/opt/plexmediaserver`; re-establish `/var/lib/plexmediaserver` symlink. Preserve Preferences.xml, database, identity and token; do not launch empty setup first. |
| Transmission | Compose, tracked settings/init hook | Restore state and credentials. Legacy completion extractor remains disabled; Unpackerr owns extraction. Preserve paused jobs and 100 KB/s download cap. |
| Unpackerr | Pinned image and hardened Compose definition | Restore `meta/appData/unpackerr/unpackerr.conf`, or generate it from restored Sonarr/Radarr API keys. Config contains secrets; do not commit plaintext. |
| Beets and Beets-audible | Compose, audiobook dependency initialization | Extract custom plugin source and nonsecret config from appData into dotjik. Keep credentials in Bitwarden, never in Git (including encrypted archives). Retain DBs and audiobook read-only config mount. |
| MariaDB | Compose | Persistent config/data is `/appData/mariadb/config`, outside the array. Restore using the logical dump and existing credentials; do not copy a running database directory. |
| Auto-m4b | Compose now has opt-in `manual` profile | Intentionally held. Review populated queue and enable backups before explicitly starting it. |
| nginx / TLS | systjik nginx config, pinned module builder and encrypted key/cert files | Supply age identity securely; verify DNS, certificates and deployment address. Do not put decrypted keys in Git. |
| Daily app backups | `etc/si-app-backup`, systemd units | Restore root-only password, existing repository and restore metadata. Never generate a different password for an existing repository. |
| Weekly offsite pull | fi user scripts/timers in dotjik | fi initiates SSH; retain fi keys/passwords. Sunday pull and daily 10:00 catch-up; onsite/public connectivity still pending. |
| Executable media guard | `etc/si-media-guard`, systemd timer | Needs restored application API access. Preserve payloads; never execute downloaded `.exe` files. |
| Firewall / SELinux | Deployment policy still needs work | Live host is permissive and exposes broad high ports. Do not reproduce this as the desired security baseline. Specify LAN/remote access and validate enforcing policy separately. |

## Provisioning changes in this pass

- Added explicit server packages: SnapRAID, Plex, rsync, sqlite, PyYAML, smartmontools and ffmpeg; added server Docker repository.
- Removed stale server fstab replay. The helper preserves OS/unrelated mounts, replaces only known array entries, rejects unknown array mounts and malformed managed blocks, and writes a timestamped backup. It checks all expected ext4 UUIDs before writing. It does not mount, format, partition, enable services or run SnapRAID.
- Docker, Compose and Plex startup are guarded by actual mounted UUID/type checks. Compose additionally requires `/etc/si-provision/services-ready`, a local operator-created marker after restoration. Do not version-control that marker.
- Docker daemon settings and new server provisioning/drop-in files are excluded on clients.
- Auto-m4b requires explicit profile selection.

## Recovery / bootstrap order

These steps are an operator runbook; they are not an unattended script. Use a fresh Fedora installation with the hostname/role configured as si. Do not apply this host-specific inventory to arbitrary disks.

1. **Establish identities.** Confirm `m` is UID/GID 1000 and `media` is UID954/GID950; containers use UID1000/GID950, while native Plex runs as media. Check existing names and numeric IDs before creating accounts. Add m to media/docker and Plex to media as appropriate. Do not renumber accounts or recursively chown the array. Automated collision-safe account creation is still outstanding.
2. **Supply secrets and sources.** Restore age identity through a private channel, bootstrap systjik with its `setup.sh`, and provision m's dotjik checkout. Review `systjik diff`. Package lists still include desktop-heavy common packages and need separation before claiming a minimal server install.
3. **Install storage prerequisites.** Resolve mergerfs packaging first. Prevent package-install auto-start of Docker/Plex on a fresh machine until storage and app state are ready. Existing systjik package/enable scripts still need staged bootstrap orchestration; do not run a blanket apply as the first recovery operation.
4. **Install the reviewed system files.** Use selective apply or a controlled installation phase. Do not run all services yet. Validate the generated fstab:

   ```fish
   sudo /usr/local/lib/tjikup/tjikup system storage --print-fstab
   # After reviewing the printed entries and attached disk UUIDs:
   sudo /usr/local/lib/tjikup/tjikup system storage --write-fstab
   sudo systemctl daemon-reload
   ```

   Create mountpoint directories, mount each physical disk, then `/mnt/storage`, and run `sudo /usr/local/lib/tjikup/tjikup system storage --check`. The helper never creates storage data directories on unmounted disks.
5. **Restore state.** Follow the application-backup recovery guide in dotjik `docs/si-application-backups.md`. Restore SQLite snapshots, configs, Plex identity, and the MariaDB logical dump with services stopped. Ensure `/home/m/downloads` links to `/mnt/storage/meta/downloads` and Plex's state symlink points at restored state. Check Compose bind sources exist and owners match; avoid Docker creating empty root-owned directories.
6. **Validate configuration.** Render m's Compose with `docker compose config --quiet`. Restore Unpackerr secrets and test Arr/Transmission/Plex connections. Review intended image tags or explicit pins and custom Beets plugins. Test `nginx -t`. Keep Radarr's disabled download client and paused torrents unchanged unless deliberately authorized.
7. **Enable services deliberately.** Create `sudo touch /etc/si-provision/services-ready` only when restore and checks pass. Enable Docker, dockers.service, Plex and nginx in dependency order; review logs and endpoints. Auto-m4b remains outside the default stack. Enable `si-app-backup.timer`, `si-media-guard.timer`, `si-snapraid-sync.timer`, `si-snapraid-scrub.timer`, and `si-snapraid-resume.service` only after credentials, storage and dataset checks pass. Never sync an empty/incomplete restore against the recovery parity.
8. **Prove recovery.** Run a backup and sample restore, check next timer runs, then test fi's pull. Rehearse the whole process on a disposable host before promising one-command provisioning.

## Remaining work toward one-command bootstrap

- [ ] Split server packages from desktop-heavy common packages.
- [ ] Verify the supported mergerfs artifact; retain intended container tags and only explicit Compose pins.
- [ ] Implement collision-safe account/directory/symlink provisioning with restore-aware ordering.
- [ ] Implement staged bootstrap that blocks package-triggered service starts until restored state is ready.
- [ ] Capture Beets custom code/config and generate Unpackerr config from secret inputs.
- [ ] Add idempotent API policy reconciliation for Arr/Plex integrations, without overwriting restored app databases.
- [ ] Define and test firewall, SELinux and onsite DNS policy.
- [ ] Rehearse on a fresh machine and record acceptance checks for every service.

Validation this pass: all 12 systjik validation tests passed, including seven storage regression tests; the new read-only mount guard passed against live si. No broad apply, upgrades, service restarts, syncs or acquisition requests were performed.
