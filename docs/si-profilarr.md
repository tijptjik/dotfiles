# Profilarr on si

Profilarr manages the shared Sonarr/Radarr policy database. The stable-channel
`profilarr` and `profilarr-parser` services are in managed Compose. The parser
is internal to Docker; nginx exposes the authenticated manager at
https://profiles.type.hk through host loopback port 6868. Cloudflare requires a
proxied CNAME `profiles` → `type.hk`, with the existing origin TLS settings.

The owner username is `admin`. The generated password and runtime API key are
saved in Bitwarden Secrets Manager, `dotfiles` / `si-profilarr`. Never commit
those values. The runtime API key is loaded from
`/mnt/storage/meta/appData/profilarr/runtime.env`; a fresh host restores this
file and Profilarr state from the normal encrypted application backup.

All persistent state is under `/mnt/storage/meta/appData/profilarr`, owned by
UID 1000/GID 950. SQLite is included in the existing online database snapshot
and encrypted daily/offsite backup flow. Known logs/cache are excluded. Profilarr
is paused with acquisition writers during guarded SnapRAID maintenance.

## Connections

| App | Internal URL | External URL |
| --- | --- | --- |
| Radarr | `http://radarr:7878` | https://movies.type.hk |
| Sonarr | `http://sonarr:8989` | https://shows.type.hk |

Connections were authenticated and their actual versions detected during setup.
Automatic replacement of existing default delay settings is disabled. Arr sync
is manual while acquisition policy is being validated. Upgrades and bulk media
renames were not configured.

## Policy source

The `si-media-profiles` PCD is at
`home/dockers/profilarr-database`. It contains the reviewed Dictionarry snapshot,
clean target names and requested tier rules. The `profilarr` branch publishes
that directory as a standalone PCD. The separate Dictionarry tab remains the
upstream catalogue for comparison.

See [the policy README](../home/dockers/profilarr-database/README.md) for all 12
names, requested tier windows, native resolution bounds, limitations and refresh
commands. Names range from `4K:1 Remux` to `SD:9`; HD means 1080p except the
explicit `HD:6 Quality @ 720p` profile.
Numbers sort from best (`1`) to lowest (`9`); the renumbering preserved profile
IDs, library assignments and all quality settings.
Numbers invert the user's explicit **OK, rescore** list, captured in dotfiles
commit `82686df`: **new number = 10 - old number**. 4K uses `1` Remux, `2` Quality,
`3` Balanced, `4` Efficient. HD uses `1` Remux, `2` Quality HDR, `3` Quality,
`4` Balanced, `5` Efficient, `6` Quality at 720p, `7` Compact; SD is `9`.
The earlier version-2 strategy codes are not the basis for these display numbers.
Name-only Arr updates and Seerr display-name updates were backed up under
`/mnt/storage/meta/appData/profilarr/backups/profile-renumbering-<UTC timestamp>`.

The source records next-tier maxima and the HD:5 Efficient minimum, but native
Arr cannot enforce cross-preset tier windows: Dictionarry presets overlap and
contain fallback releases. The snapshot keeps curated scoring, enforces a 1080p
floor for Efficient and higher, and prevents resolution jumps. Exact tier-window
classification is not a native feature; the curated presets and resolution
guards are active. Seerr retains its existing 4K:3 Balanced movie default and
uses HD:4 Balanced for TV and anime.

Legacy assignments were migrated using the user-approved mapping in
`home/dockers/profilarr-database/legacy-migration.json`. All 13 legacy profiles
were removed after migrating media, import lists, collections, Seerr defaults
and saved request references. Paths, monitoring and tags were preserved.
Profiles and quality definitions use manual Arr sync. Naming, delay profiles,
download clients and automated
backlog/upgrade searches are not configured by this policy.

Sonarr's old global Dolby Vision ban is disabled so curated HDR profiles can
apply their own rules. The global executable restriction also uses suffix
boundaries. The former legacy-only Dolby Vision CF has no nonzero scores on the
new profiles.

State and UI overrides are in the application backups; secrets remain in
Bitwarden. Publish reviewed source changes explicitly; do not use a profile's
requested bounds as evidence of native enforcement.

## Explicit legacy migration

The approved mapping and migration tool are versioned. This is a manual operation
and is never invoked by chezmoi, chezetc or tjikup:

```sh
sudo python3 /home/m/.local/share/chezmoi/home/dockers/profilarr-tools/executable_migrate-legacy-profiles.py
# After reviewing that dry run:
sudo python3 /home/m/.local/share/chezmoi/home/dockers/profilarr-tools/executable_migrate-legacy-profiles.py --apply
```

The tool checks profile identities, makes native Arr backups, and stores private
configuration/assignment snapshots below
`/mnt/storage/meta/appData/profilarr/backups/profile-migration-<UTC timestamp>`.
It uses bulk profile-only media edits and per-ID collection updates, preserving
monitoring and paths. It does not start a search or move files. Approved Seerr
request references require a short stopped-writer SQLite transaction because the
API refuses to edit approved requests; all other request fields stay unchanged,
and no approval hooks/notifications run. Seerr is restarted even on failure.

Verification covers every existing media assignment, dependent defaults, all 12
remaining profiles and both Seerr request dropdowns. Profilarr's library caches
must be refreshed after the migration so its cards show the new assignments.
Use the native backups and private snapshots for a guarded rollback if needed;
restoration is never automatic.
