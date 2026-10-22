# si Dictionarry acquisition profiles

`policy.json` records the clean names, requested tier windows and the settings
native Arr profiles can actually enforce. The generated SQL contains public
Dictionarry policy only, without credentials, library inventory or app databases.
Upstream attribution is in `UPSTREAM-LICENSE`.

| Profile | Dictionarry preset | Requested maximum | Requested minimum |
| --- | --- | --- | --- |
| `4K:9 Remux` | 2160p Remux | `4K:9 Remux` | `HD:5 Efficient` |
| `4K:8 Quality` | 2160p Quality | `4K:9 Remux` | `HD:5 Efficient` |
| `4K:7 Balanced` | 2160p Balanced | `4K:8 Quality` | `HD:5 Efficient` |
| `4K:6 Efficient` | 2160p Efficient | `4K:7 Balanced` | `HD:5 Efficient` |
| `HD:9 Remux` | 1080p Remux | `HD:9 Remux` | `HD:5 Efficient` |
| `HD:8 Quality HDR` | 1080p Quality HDR | `HD:9 Remux` | `HD:5 Efficient` |
| `HD:7 Quality` | 1080p Quality | `HD:8 Quality HDR` | `HD:5 Efficient` |
| `HD:6 Balanced` | 1080p Balanced | `HD:7 Quality` | `HD:5 Efficient` |
| `HD:5 Efficient` | 1080p Efficient | `HD:6 Balanced` | `HD:5 Efficient` |
| `HD:4 Quality @ 720p` | 720p Quality | `HD:4 Quality @ 720p` | None |
| `HD:3 Compact` | 1080p Compact | `HD:5 Efficient` | None |
| `SD:1` | SD | `SD:1` | None |

## Native settings and pending tier rules

The clean names identify each target. Maximum means the next higher tier at the
same resolution, capped at the highest available tier. The requested shared
minimum is HD:5 Efficient, except lower targets have no minimum.

Dictionarry presets overlap; they do not classify releases into disjoint numbered
bands. Each preset also contains lower-quality fallbacks. Native Arr quality
profiles cannot directly express acceptance by one complete preset, rejection
above another preset, and a separate target preset. The cross-preset tier window
is recorded as a requested policy and is **not enforced** by this snapshot.
It requires a separate classifier or a simpler native policy choice.

The snapshot does enforce a 1080p resolution floor for HD:5 Efficient and higher,
a 720p ceiling for HD:4 Quality @ 720p, and the appropriate 1080p/2160p ceilings.
Lower targets retain the curated SD fallbacks. SD:1 permits known SD qualities up
to 576p, any bitrate/codec, and has no automatic upgrades. These resolution bounds
are enforced on allowed qualities and group members; a name change alone is not
used as a guard. Dictionarry scores and upgrade cutoffs are retained, with an
additional executable rejection. Remux is allowed only by the Remux presets.

Native custom-format names have a `DI: ` prefix to preserve formats used by
legacy library profiles. Existing library assignments remain in place. Sonarr's
legacy Dolby Vision rule uses a boundary-aware CF on legacy profiles; curated
profiles apply their own HDR rules. Its global executable rule also uses suffix
boundaries to avoid Batman/Adventure false positives.

Global size definitions are Dictionarry's unrestricted limits. No bitrate-based
quality classification, renaming job, backlog search or upgrade job is added.
Seerr keeps its previous defaults until the tier-policy choice is resolved.

## Refresh and publish

Check out the reviewed Dictionarry revision from `policy.json` and schema 1.1.0
outside this repository. Review upstream changes before updating the revision.
Regenerate and validate:

```sh
python3 home/dockers/profilarr-tools/executable_build-dictionarry.py \
  --upstream /path/to/dictionarry-database --schema /path/to/schema
python3 home/dockers/profilarr-tools/executable_build-dictionarry.py \
  --upstream /path/to/dictionarry-database --schema /path/to/schema --check
python3 home/dockers/profilarr-tools/executable_check-policy.py --list
```

After committing, run
`python3 home/dockers/profilarr-tools/executable_publish-database.py`.
Manually sync the `si-media-profiles` source database in Profilarr, review the
exported profiles, then sync the selected quality profiles to Arr. Source sync
and Arr sync are separate actions. Keep conflict handling at `ask`.

UI overrides live in backed-up SQLite state; promote accepted changes to this
source before publishing. Never store API keys or credentials in Git.
