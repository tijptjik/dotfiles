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
`home/dockers/profilarr-database`. It contains the reviewed Dictionarry policy
snapshot, the public upstream revision, the SD profile and user-facing aliases.
The `profilarr` branch of this repository publishes that directory as a PCD root.
The separate Dictionarry tab remains the upstream catalogue for comparison.

See [the policy README](../home/dockers/profilarr-database/README.md) for the exact
code mapping, generated snapshot, refresh/publish commands and limitations.

Each of the 12 acquisition choices has the form
`@ {strategy} | mx {strategy} | mn SD`. For example:
`@ HD/6:BAL | mx HD/6:BAL | mn SD` is Dictionarry 1080p Balanced, including its
lower-resolution fallbacks. The default for new Seerr movie/series requests is
that Balanced choice. Existing library profile assignments remain in place.

These are curated strategies, not disjoint bitrate bands. The initial catalogue
uses target = maximum. Remux strategies are allowed, and an SD-only profile is
included. No arbitrary cross-strategy ranges or codec-adjusted bitrate rules are
implied by the names. The former custom bitrate design is superseded.

Profiles and global quality definitions are selected for manual Arr sync.
Dictionarry's global size definitions remove size caps; this affects all profiles
in the Arr instance. Naming, delay profiles, download clients, library assignments
and automated backlog/upgrade searches are not part of this change.

Namespaced custom formats preserve the existing profiles' format definitions.
Profilarr state and UI overrides are included in the application backups; secrets
remain in Bitwarden. The source snapshot is versioned and refreshed explicitly.
