# si media policy

This is the Profilarr-compliant database for si. Its source lives in the main
dotfiles checkout at `home/dockers/profilarr-database`. The `profilarr` branch of
the same public repository publishes this directory as a standalone PCD root.
It contains policy only, without credentials, library contents or app databases.

`policy.json` defines the seven media tiers and acquisition-profile notation:

| Code | Media tier |
| --- | --- |
| `4K/X` | Archival: encoded 4K, unrestricted bitrate/size |
| `4K/H` | 4K High |
| `4K/L` | 4K Low |
| `HD/H` | 1080p High |
| `HD/M` | 1080p Low |
| `HD/L` | 720p |
| `SD` | SD, unrestricted bitrate |

The user-facing acquisition name is
`@ {upgrade target} | mx {maximum accepted} | mn {minimum accepted}`.
For example, `@ 4K/H | mx 4K/H | mn HD/M` accepts a 1080p Low fallback and
targets 4K High. Minimum must not exceed target; target must not exceed maximum.
Releases above the target remain eligible when the maximum permits them.

The sibling `profilarr-tools/check-policy.py` validates notation against an
already-classified media tier. For example, the profile above accepts `HD/M`,
`HD/H`, `4K/L`, and `4K/H`; it rejects `HD/L`, `SD`, and `4K/X`. The checker does
not classify release bitrates or modify any acquisition settings.

The shared safety/codec formats have parser regression fixtures. They are
definitions, and become active only when selected and scored in an acquisition
profile. Existing Arr profiles remain in place while the bitrate enforcement
policy is selected and validated. The native Arr APIs cannot directly express
codec-adjusted bitrate bounds per acquisition profile on the installed versions.

Profilarr UI overrides are stored in its backed-up SQLite state. Promote accepted
changes to the source directory and publish the PCD branch to version them in Git.
Keep conflict handling at `ask` so a source update cannot silently discard a local
override.
