# si Dictionarry acquisition profiles

The catalogue uses Dictionarry's curated source, encoder, audio and release-group
scoring. `policy.json` records the upstream revision, names and Seerr default.
`ops/1.dictionarry-acquisitions.sql` is a reproducible public policy snapshot,
with attribution in `UPSTREAM-LICENSE`. It contains no credentials or media lists.

| Code | Dictionarry strategy |
| --- | --- |
| `HD/9:MAX` | 1080p Remux |
| `HD/8:HDR` | 1080p Quality HDR |
| `HD/7:HQ` | 1080p Quality |
| `HD/6:BAL` | 1080p Balanced |
| `HD/6:EFF` | 1080p Efficient |
| `HD/4:XSQ` | 720p Quality |
| `HD/3:XS` | 1080p Compact |
| `4K/9:MAX` | 2160p Remux |
| `4K/7:HQ` | 2160p Quality |
| `4K/6:BAL` | 2160p Balanced |
| `4K/6:EFF` | 2160p Efficient |
| `SD` | SD |

## Acquisition choices

Each strategy has one user-facing profile:
`@ {strategy} | mx {strategy} | mn SD`. The SD-only choice is
`@ SD | mx SD | mn SD`. The default for new requests is
`@ HD/6:BAL | mx HD/6:BAL | mn SD`.

`@` identifies the upgrade strategy; `mx` identifies the maximum strategy;
`mn SD` retains the curated lower-resolution fallbacks. This initial list uses
`@ = mx`: it does not pretend that overlapping Dictionarry strategies are strict,
interchangeable bitrate bands. BAL and EFF are alternatives. Their descriptions'
file sizes are typical outcomes, not hard limits. Arbitrary target/max/min
combinations are not configured.

Upstream scoring, language rules, quality groups and upgrade cutoff are retained.
The 720p variant removes upstream's enabled HDTV-1080p member to honor its ceiling.
The new SD profile allows DVD, SDTV, 480p WEB/Bluray and 576p Bluray, with no
bitrate or codec restriction and no automatic upgrades. It retains known-bad
release, executable, full-disc and original/English audio protections.
MAX profiles permit remuxes. Full-disc payloads remain excluded. The old
codec-adjusted bitrate design and encoded-only Archival exclusion are superseded.

CF names are prefixed `DI: ` so importing these profiles does not replace formats
used by the existing library. An additional boundary-aware executable rejection
is included in every profile. Upstream global size definitions have minimum 0,
maximum unlimited; they replace the old global caps that conflict with Compact
and Remux. This change applies to every profile in each Arr instance.

Existing library assignments are not migrated. New profiles and Seerr defaults
can be changed independently of a future library migration. No backlog search
or Profilarr upgrade job is configured by this catalogue.

## Refresh and publish

Check out the reviewed Dictionarry revision and schema 1.1.0 outside this repository.
To change versions, review the upstream changes and update `policy.json` first.
Then regenerate, validate and commit the public snapshot:

```sh
python3 home/dockers/profilarr-tools/executable_build-dictionarry.py \
  --upstream /path/to/dictionarry-database --schema /path/to/schema
python3 home/dockers/profilarr-tools/executable_build-dictionarry.py \
  --upstream /path/to/dictionarry-database --schema /path/to/schema --check
python3 home/dockers/profilarr-tools/executable_check-policy.py --list
```

After committing, publish with
`python3 home/dockers/profilarr-tools/executable_publish-database.py`, then manually
sync the `si-media-profiles` database in Profilarr, review its diff, and sync the
selected quality profiles and quality definitions to Arr. Source and Arr syncs
are separate actions. Namespaced formats, curated scoring and acquisition names
are versioned together; unreviewed upstream changes cannot silently alter them.

Profilarr UI overrides live in its backed-up SQLite state. Promote accepted
changes to this source before publishing. Keep conflict handling at `ask`.
