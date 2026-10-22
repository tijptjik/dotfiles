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
commands. Names range from `4K:9 Remux` to `SD:1`; HD means 1080p except the
explicit `HD:4 Quality @ 720p` profile.

The source records next-tier maxima and the HD:5 Efficient minimum, but native
Arr cannot enforce cross-preset tier windows: Dictionarry presets overlap and
contain fallback releases. The snapshot keeps curated scoring, enforces a 1080p
floor for Efficient and higher, and prevents resolution jumps. Exact tier-window
classification is pending a separate policy decision. Seerr's previous defaults
remain in place while that decision is pending.

Existing library assignments are preserved. Profiles and quality definitions
use manual Arr sync. Naming, delay profiles, download clients and automated
backlog/upgrade searches are not configured by this policy.

Sonarr's old global Dolby Vision ban is disabled so curated HDR profiles can
apply their own rules. Legacy profiles retain a boundary-aware Dolby Vision CF;
the global executable restriction also uses suffix boundaries.

State and UI overrides are in the application backups; secrets remain in
Bitwarden. Publish reviewed source changes explicitly; do not use a profile's
requested bounds as evidence of native enforcement.
