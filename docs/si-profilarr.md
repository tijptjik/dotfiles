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

The custom PCD is at `home/dockers/profilarr-database` in the main dotfiles
checkout. Its `policy.json` contains the media tiers, x264-equivalent target
bands and acquisition notation. Publish the committed directory as the
`profilarr` branch of the same repository:

```sh
cd ~/.local/share/chezmoi
python3 home/dockers/profilarr-tools/executable_publish-database.py
```

The publisher commits only the subtree to its own branch and uses a normal
fast-forward push. It leaves the current checkout in place. Profilarr links
`https://github.com/tijptjik/dotfiles`, branch `profilarr`, without a GitHub token.
Local UI overrides remain in its backed-up database; promote accepted changes
into the source directory and republish to version them. Conflict strategy is
`ask`. Scheduled source sync is disabled; an explicit source sync pulls the
published branch. Arr acquisition-profile sync remains a separate manual step.

The shared executable/disc, Dolby Vision and codec conditions have 19 regression
fixtures verified against Profilarr's .NET parser, including Adventure and Batman
false-positive cases. Their definitions do not change existing Arr restrictions
until a selected acquisition profile is synced.

## Acquisition names

Use `@ {target} | mx {maximum} | mn {minimum}` with the exact codes in
`policy.json`: `4K/X`, `4K/H`, `4K/L`, `HD/H`, `HD/M`, `HD/L`, `SD`.
`HD/M` means 1080p Low; `HD/L` means 720p. The user's example normalizes to
`@ 4K/H | mx 4K/H | mn HD/M`.

The minimum must not exceed the target, and the target must not exceed the
maximum. A release above the target can be initially acquired when the maximum
allows it. Target is the upgrade stopping point; maximum is an acceptance bound.
Archival is an exception policy permitting encoded 4K at unrestricted bitrate,
with remuxes and full-disc payloads still excluded.

Activation awaits the bitrate-policy choice: native preferences, or additional
strict release-selection logic. Installed Sonarr 4 and Radarr 6 expose global
runtime-based size limits and fixed-GB per-profile size conditions; these cannot
directly enforce per-profile codec-adjusted bitrate bounds. Existing profile
assignments and Seerr defaults remain in place pending that choice.
