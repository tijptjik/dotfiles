# Rose Punk icon system

Run commands from the repository root. The build is offline and uses committed
inputs; it never inventories the host's applications, installs themes, changes
desktop settings, or records artwork approval.

```sh
python3 -B scripts/icons/release.py check
python3 -B scripts/icons/release.py build
python3 -B scripts/icons/release.py package
```

`check` is the release gate. It renders every producer and compares output bytes
and theme membership with the checkout, including stale files and aliases.
`build` validates and renders everything before updating generated files. It
retires stale SVGs only inside the two generated icon directories. `package`
requires a passing check and writes an installable `rose-punk.zip` and
`release.json` to ignored `.local/icon-releases/` (`--output DIR` overrides it).
ZIP aliases are ordinary SVG copies, independent of Chezmoi. Source attribution
and vendored license texts accompany the download.

The manifest records source/output SHA-256 hashes and renderer versions. ZIP
entries have fixed timestamps, permissions, and ordering. Reproduce with the
same rendering stack; librsvg, Cairo, ImageMagick, Pillow and zlib versions can
affect bytes. `check` detects that drift. A passing build verifies reproducible
assets; it does not assert final visual approval or publish a release.

## Build dependencies

Use Python 3.12+ with PyGObject/librsvg, pycairo and Pillow, plus ImageMagick's
`magick` command. On Fedora these are supplied by `python3-gobject`, `librsvg2`,
`python3-cairo`, `python3-pillow` and `ImageMagick`. Use the interpreter where
those modules are installed. Every fleet label has an explicit SVG mapping;
font discovery and installed fonts are not build inputs.

## Sources and generated outputs

| Part | Authoritative inputs | Generated output |
| --- | --- | --- |
| Desktop theme | `catalog.json`, `provenance.json`, `local/`, `upstream/`, `references/`, palette/material modules | `home/dot_local/share/icons/rose-punk/scalable/apps/` |
| Shell and launcher companions | `command_icons.py`, `command-icons.json`, `material_art.py:COMMAND_ART` | Primary theme SVGs and `local/` source snapshots |
| Aliases | Catalog icon names/desktop IDs and `alias-overrides.json` | `theme-aliases.json` and Chezmoi `symlink_*.svg` files |
| Fleet terminal sprites | `fleet.py` SVG mapping and `scripts/fleet_update/icon_catalog.py` labels | `scripts/fleet_update/icons32.json` |
| Homepage | `homepage.json` and its source SVG/hash declarations | `home/dockers/homepage/images/rose-punk/` |

`apps.json` is the explicit desktop coverage policy used by `audit.py`; it is
not regenerated from a particular host. `retired.json` preserves retired catalog
and provenance records. Vendored references retain their licenses and hashes.
Source edits require corresponding provenance/hash updates. Build validation
rejects missing/changed sources, retired entries and ambiguous aliases.

`fullset.py` assembles the primary SVGs using `illustrated.py` (shared tile),
`build.py`/`extra_art.py` (retained original geometry), `palette.py`,
`materials.py`/`material_art.py` and `frameless.py` (optical sizing).
`icon_data.py` owns source validation, paths, aliases and generated file writes.
`homepage.py`, `fullset.py` and `build-fleet.py` remain individual build entry
points; use `release.py` to verify the complete system before committing.

## Installation and theme selection

Chezmoi deploys the named `rose-punk` theme. The apply hook runs `install.py` to
refresh caches and retire old icon overrides. It migrates the old
`rose-punk-illustrated` selection only after the new primary theme is installed,
while preserving other theme choices. `choose.py` explicitly selects a theme;
`check-theme.py` reports host-specific lookup problems; `audit.py` reports local
coverage. These commands are separate from the offline release gate.

The standalone Tjikup notification fallback belongs to tjikOS's installer;
the icon build never writes `home/dot_local/share/icons/tjikup.png`.

## Optional reviews and historical studies

`gallery.py` produces the current catalog and contact sheets without requiring
historical review files. Both the current previews and release gallery include
application originals from `catalog.json` and shell companions from
`command-icons.json`. Runtjik's internal launcher controls stay in the installed
theme and release ZIPs, but are excluded from application reviews and the
type.hk gallery. Their dedicated study is `command_icons.py --preview`;
their attribution manifests accompany the release ZIP.
`frameless-review.py` exports the current originals
with optional frozen comparisons. `palette-review.py`, `material-review.py`,
`coherence-review.py`, and `homepage-coherence-review.py` are historical review
tools: they can require local snapshots that are deliberately not release
inputs. `review_paths.py` keeps their outputs under ignored
`.local/icon-reviews/`. They are never invoked by the release build or check.

`archive/outline/` retains the earlier outline study outside managed icons.
`build.py` and `compare.py` can recreate that study; they do not define the
primary theme. `plex-globe.py` is an optional authoring tool requiring Shapely
and an external Natural Earth dataset; the resulting SVG is vendored, so the
dataset and authoring dependencies are not needed to release.

`framed.py status|approve|build` is the secondary Rose Punk Framed workflow.
It requires explicit final artwork sign-off and verifies every primary hash and
alias before deriving the framed set. Ordinary builds never approve it. Its
optional ZIP and manifest also live under `.local/icon-reviews/`.

## Validation

```sh
python3 -B -m unittest discover -s tests -p 'test_icon_*.py' -v
python3 -B -m unittest discover -s tests -p 'test_rose_punk_icons.py' -v
bash scripts/validate.sh
```

Tests with frozen local review archives are optional. Release verification must
also pass from a clean checkout without those archives; `release.py check`
checks the committed generated assets directly.

## Cut and publish a version

Release payloads live in `tjikos-assets/typehk/rose-punk-releases/<version>/`
on Cloudflare R2. Git retains source artwork, producers and the small type.hk
registry/gallery presentation manifests. Generated ZIPs, release gallery SVGs,
checksums and renderer manifests stay outside the site's `public/` directory.

From Tijpfiles, this command cuts both installable themes, prepares the type.hk
registry and gallery, uploads the snapshot to R2, verifies every downloaded
artifact by SHA-256, then deploys the site and verifies the public downloads:

```sh
python3 -B scripts/icons/release.py cut --version 0.1.0-rc.1 \
  --site /home/io/code/type.hk --deploy
```

Choose a fresh version for each uploaded, pushed or deployed release. `cut` is
an explicit release decision: it authorizes deriving the framed counterpart of
that exact frameless snapshot. It does not change the historical study approval
file or install either theme. Ordinary `build`, `check` and `package` stay offline.

The output is `.local/icon-releases/<version>/`: both ZIPs (including aliases,
attribution and licenses), a gallery snapshot, source/output hashes, renderer
versions, source commit/dirty status and `SHA256SUMS`. Site registration keeps an
offline copy under the site's ignored `.local/rose-punk-releases/`; only
`public/rose-punk-releases/registry.json` and `index.html` are site release files.

Repeat `cut` with the same version only while it is unpublished. Its previous
snapshot is retained until a replacement finishes building. Deployment attempt
records and pushed registry entries lock versions. Remote access errors block
replacement; fetch unknown remote commits in the site checkout and retry. R2
uploads use checksum comparison and immutable mode, so different existing release
bytes are rejected even if local records are missing. Pass the same `--site` when
recutting. The offline check must pass; run `build` first if intentional source
edits made generated outputs stale.

Omit `--deploy` to prepare the registry without uploading or publishing. Omit
`--site` too for a completely local rehearsal (`--output /tmp/icon-releases` can
keep test versions separate). Retry an upload, build or deployment failure using
the existing snapshot:

```sh
python3 -B scripts/icons/release.py publish --version 0.1.0-rc.1 \
  --site /home/io/code/type.hk --deploy
```

The registry remains at `https://type.hk/rose-punk-releases/registry.json` and the
gallery/download URLs stay unchanged. The site Worker streams their bytes from
R2. Existing versions are retained; the explicitly published version becomes
`latest`. A deployment attempt marker locks the snapshot before upload, and a
success receipt is written only after public verification passes. Network or
verification failure returns nonzero, even if Cloudflare accepted the deployment.

Publication requires the site's Bun dependencies, Cloudflare credentials and the
configured `r2-tijpdata` rclone remote with access to `tjikos-assets`. Upload
receipts are kept under the site's ignored `.local/r2-receipts/`. The publisher
refuses unrelated uncommitted site changes; commit or isolate them first. It does
not commit, tag, push, update Homepage on Si, or change installed desktop icons.
