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

The standalone Tjikup notification fallback belongs to Tooltjik's installer;
the icon build never writes `home/dot_local/share/icons/tjikup.png`.

## Optional reviews and historical studies

`gallery.py` produces the current catalog and contact sheets without requiring
historical review files. Both the current previews and release gallery include
application originals from `catalog.json` and shell/launcher companions from
`command-icons.json`; their attribution manifests accompany the release ZIP.
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

From Tijpfiles, this single command cuts both installable themes, updates the
static type.hk release registry and gallery, then deploys and verifies the public
manifest and ZIP hashes:

```sh
python3 -B scripts/icons/release.py cut --version 0.1.0-rc.1 \
  --site /home/io/code/type.hk --deploy
```

Choose a fresh version for each pushed or deployed release. `cut` is an explicit release decision:
it authorizes deriving the framed counterpart of that exact frameless snapshot.
It does not change the historical study approval file or install either theme.
Ordinary `build`, `check` and `package` still never approve artwork or deploy.

The output is `.local/icon-releases/<version>/`: both ZIPs (including aliases,
attribution and licenses), a gallery snapshot, source/output hashes, renderer
versions, source commit/dirty status and `SHA256SUMS`. Repeat `cut` with the same
version to replace an unpublished snapshot and its local site registration.
The old snapshot is retained until its replacement finishes building. Versions
with deployment records or release files in the site's remote Git history
cannot be overwritten. Replacement checks current remote refs; remote access
errors block replacement. If a remote commit
is missing locally, fetch it in the site checkout and retry. Pass the same
`--site` when recutting to check its remotes and refresh its registry.
Restart a running Vite dev server after replacing a release directory if a new
gallery image is missing: its cached public-file list can return the HTML
fallback for a new SVG path. Rebuild before checking a Vite production preview.
The existing offline check must pass; run `build` first if
intentional source edits made generated assets stale.

Omit `--deploy` to prepare the registry without publishing. Omit `--site` too
for a completely local release rehearsal (`--output /tmp/icon-releases` can
keep test versions separate). To retry a failed site build or deployment, use
the existing immutable snapshot instead of cutting it again:

```sh
python3 -B scripts/icons/release.py publish --version 0.1.0-rc.1 \
  --site /home/io/code/type.hk --deploy
```

The registry is served at `https://type.hk/rose-punk-releases/registry.json`;
its download index is linked from the theme page. Existing versions are retained;
the explicitly published version becomes `latest`. The gallery uses the same
versioned assets. The command runs the site's `bun run check` and `bun run deploy`
and then checks public download hashes. A deployment attempt marker locks the
snapshot before uploading; a success receipt is written only when verification
passes. Network or verification failure returns nonzero, even
if Cloudflare already accepted the deployment; retry `publish` after resolving it.

Deployment requires the site's Bun dependencies and Cloudflare credentials.
It refuses unrelated uncommitted site changes so a theme release cannot silently
publish other unfinished pages. Commit or isolate those changes first. The
command does not commit, tag, push, update Homepage on Si, or change installed
desktop icons.
