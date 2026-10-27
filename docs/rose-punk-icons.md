# Rose Punk icons

Rose Punk is the primary transparent icon theme, installed under directory ID
`rose-punk`. The current catalog contains 107 app and service icons. It also
supplies all fleet terminal sprites; fourteen separate service illustrations
are generated for Homepage. These share source artwork and palette rules, with
separate inventories and deployment paths.

The [icon tooling guide](../scripts/icons/README.md) documents source ownership,
build dependencies, reproducible release commands, and historical review tools.
The [style guide](rose-punk-icon-style-prompt.md) defines the artwork treatment.

## Build and release

From the repository root:

```sh
python3 -B scripts/icons/release.py check
python3 -B scripts/icons/release.py build    # after intentional source changes
python3 -B scripts/icons/release.py package
```

The offline release gate renders desktop SVGs, aliases, fleet sprites and
Homepage SVGs and compares every generated file with the checkout. It requires
no application inventory or ignored review snapshots. Source SHA-256 checks run
before output changes. Stale generated SVGs and retired aliases are removed by
`build`; conflicting aliases fail validation.

`package` requires a passing check. It writes an installable
`.local/icon-releases/rose-punk.zip` and `release.json` with source/output hashes
and renderer versions. The ZIP uses fixed entry metadata and regular SVG copies
for aliases, together with attribution and license texts. Reproducing exact
output requires the recorded rendering stack.
Builds do not deploy, publish, change theme settings, or record visual approval.

Source geometry, attribution and licenses are retained under
`scripts/icons/local/`, `upstream/`, `references/`, `catalog.json` and
`provenance.json`. Retired records remain in `retired.json`; build inputs are
committed alongside the generators and outputs. App names and trademarks remain
with their owners; themed adaptations are unofficial.

## Installation and theme choice

Chezmoi deploys **Rose Punk** under `~/.local/share/icons/rose-punk/`. It inherits
Neuwaita, Adwaita and hicolor for missing icons. Managed application launchers
use ordinary upstream icon names. Aliases live inside Rose Punk's own theme;
its artwork is not injected into hicolor or forced through desktop icon fields.

The client hook runs `scripts/icons/install.py` to refresh caches, retire old
hicolor links into Rose Punk themes, and restore launcher icon fields while
preserving edited launch commands. Recovery evidence lives under
`~/.local/state/rose-punk-icons/`. Unknown edited overrides remain for review.
The installer preserves other theme selections. It migrates a
`rose-punk-illustrated` selection to `rose-punk` only after the new primary theme
is installed.

```sh
python3 scripts/icons/choose.py            # select Rose Punk
python3 scripts/icons/choose.py Neuwaita   # select another installed theme
python3 scripts/icons/check-theme.py       # report host-specific lookup issues
python3 scripts/icons/audit.py             # report local desktop coverage
```

Absolute icon paths can bypass theme lookup. Keep original vendor/PWA icons as
fallbacks and fix individual missing icons rather than copying themed artwork
into hicolor. Tjikup requests `tjikup-notification` by name; Tooltjik's installer
owns its original fallback PNG. The icon build generates only the fleet sprite
JSON, not a standalone managed `tjikup.png`.

## Reviews and secondary framed set

Current local artifacts, when generated:

- [Searchable catalog](../.local/icon-reviews/docs/rose-punk-icons-gallery.html)
- [Frameless originals](../.local/icon-reviews/docs/rose-punk-icons-frameless.html)
- [Original versus themed review](../.local/icon-reviews/docs/rose-punk-color-review.html)
- [Homepage review](../.local/icon-reviews/docs/rose-punk-homepage-review.html)

These optional outputs live under ignored `.local/icon-reviews/`. Frozen
snapshots and historical comparisons are separate from canonical sources and
are not required to reproduce a release. The old outline study is preserved in
`scripts/icons/archive/outline/`, outside the managed theme tree.

Rose Punk Framed is derived from final approved primary originals, with the
same catalog and aliases. Final visual sign-off remains a separate step:

```sh
python3 scripts/icons/framed.py status
# Only after explicit artwork sign-off:
python3 scripts/icons/framed.py approve
python3 scripts/icons/framed.py build
```

Approval records exact primary SVG hashes and aliases in
`scripts/icons/frameless-approved.json`. Changed inputs invalidate it. The framed
builder preserves source geometry and paint under a uniform 6/7 scale, centered
on the flat tile at (32, 31). It writes the managed `rose-punk-framed` theme and
an installable ZIP/manifest under `.local/icon-reviews/docs/assets/icon-framed/`.
Ordinary release and review commands never create approval or the framed set.

## Runtjik command companions

Seven original frameless SVGs cover `/refresh`, `/pin`, `/grid`, `/list`, `/stats`,
`/config`, and `/shortcuts` (`/bindings` shares the shortcuts icon). They are
companion controls rather than applications, so they do not change the app
catalog or appear in application icon reviews or the type.hk gallery. They
remain in the installed theme and release downloads, with their own size study.
Their object forms and material paint live in `COMMAND_ART` in
`scripts/icons/material_art.py`. The editable originals are
`scripts/icons/local/runtjik-*.svg`; `scripts/icons/command-icons.json` records
meanings, provenance, hashes and optical sizing.

```sh
python3 scripts/icons/command_icons.py --preview
python3 -B -m unittest discover -s tests -p 'test_runtjik_command_icons.py' -v
```

The ordinary `fullset.py` renderer includes these companions, so later rebuilds
retain them. The focused command builder updates only its own seven originals,
theme files and aliases. It does not rebuild other application artwork.
The size study is `.local/icon-reviews/docs/rose-punk-command-icons.svg` (and
`.png`), showing 24, 32, 48, 64 and 96 px beside the unchanged frozen camera.
Deployment copies the seven theme files and refreshes the selected theme cache;
Runtjik resolves them through the same icon loader as application artwork.

## Versioned publication to type.hk

Use `python3 -B scripts/icons/release.py cut --version VERSION --site /home/io/code/type.hk --deploy`
to cut both frameless and framed downloads, register them with the public icon
gallery, and deploy type.hk. This explicit release action authorizes the framed
derivative of that snapshot; ordinary builds remain offline. See the
[release command and retry instructions](../scripts/icons/README.md#cut-and-publish-a-version).
Repeating `cut` can overwrite a snapshot and its site registration until that
version is pushed or deployed. Replacement requires a successful publication
check; published versions require a new version number.
