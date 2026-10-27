# Rose Punk application icons

Icon galleries, comparison snapshots and rendered previews are local review
artifacts under `.local/icon-reviews/docs/`, which Git ignores. They are
not required to build or deploy icons. The links below open that local archive.

**Rose Punk** is the primary frameless set. **Rose Punk Framed** is the secondary
set, to be generated from the final approved frameless originals. Final artwork
sign-off is still pending.

The selected illustrated direction contains **106 app and service icons**,
including artwork for all **40 fleet labels**. The original launcher inventory
covered 127 desktop IDs in 102 app families. The coverage audit includes
user, system and
Flatpak desktop directories. Hidden/NoDisplay entries are excluded. Alternate
versions and duplicate desktop entries share one family icon.

[Browse the searchable full catalog](../.local/icon-reviews/docs/rose-punk-icons-gallery.html), with previews
from 24 to 96 px. [Review the retained identity redraws](../.local/icon-reviews/docs/rose-punk-icons-redrawn.svg).
Printable contact sheets: [1](../.local/icon-reviews/docs/rose-punk-icons-catalog-1.svg),
[2](../.local/icon-reviews/docs/rose-punk-icons-catalog-2.svg), [3](../.local/icon-reviews/docs/rose-punk-icons-catalog-3.svg),
[4](../.local/icon-reviews/docs/rose-punk-icons-catalog-4.svg).

[Review the primary frameless set](../.local/icon-reviews/docs/rose-punk-icons-frameless.html),
with all 106 icons enlarged and balanced without the shared plum tile. The
comparison retains historical framed snapshots; these are not the future
Rose Punk Framed set.

Firefox and GIMP retain authentic upstream logo geometry. Mullvad retains its face and hat with a slightly smoother neck edge. Firefox
wraps a blue globe; Transmission retains its original red handle, metal housing and downward arrow. The primary set has transparent backgrounds. Symbol artwork retains its detail,
including app-specific backings and borders. The secondary framed set will add
a solid `#26233a` tile with a muted `#555169` outline at 45% opacity, without a
gradient, highlight rim or drop shadow.
Other illustrations preserve their app's visual identity while remapping its
colors with the material palette described below.

There are no unused extra-coverage apps in the active catalog; Blender and Figma are archived. Audacity, Inkscape,
LibreOffice, Edge, Teams, Notion, Slack and VS Code were dropped from the themed
catalog. Removed applications also have their artwork and aliases retired.

[Review the 92 refined icons](../.local/icon-reviews/docs/rose-punk-icons-gallery.html?refined=1), including
separate Zed Stable (white) and Preview (electric blue) entries. Each retained
channel has its own desktop mapping; Nightly is retired. Zen uses concentric rings; Strata uses its
actual installed upstream logo. Flat OBS, mpv, Sublime and Zed references are
retained under `scripts/icons/upstream/`, with provenance and hashes recorded.
The other focused redraws use editable SVG sources under `scripts/icons/local/`.
White foregrounds and semantic accents preserve contrast; Weather has a yellow
sun, and Passwords and Keys uses a purple card.

Rygel Preferences and GRASS GIS are retired from the icon set because they are no longer used. This artwork pass does not uninstall applications.

Java Monitor is part of `java-25-openjdk-devel`; a managed hidden desktop override
removes its launcher while retaining the JDK/compiler. Kimi's FirefoxPWA site was
unregistered and Toolbox's executable removed; IDE installations and settings
were retained. RustDesk, Metadata Cleaner, Homeworld, Tramoramic and Witcher had
no remaining installation found on this host; their stale catalog assets were
retired. Downloaded installers and personal data were left intact.

[Review the coherence pass](../.local/icon-reviews/docs/rose-punk-coherence-review.html): Spotify now shares
Audio Player’s mint ramp, and Collie has a sable coat, tipped ears and facial
detail matching Prowlarr. Nine local Homepage illustrations were revised as a
set: Seerr is a violet anime iris, Radarr and Sonarr share instrument materials,
and Feishin is a mint record player. Books, ribbon and monitoring glasses share
a restrained palette and meaningful material detail. Plex, Tautulli, Transmission,
Prowlarr and Telegram retain their established artwork.

The preceding desktop refinements remain in place:
GIMP and Flatpak have complementary colours; Mullvad has a slightly smoother neck;
Spotify and Solaar have ivory marks. Text Editor is crisper and Tippecanoe uses
gentler map colours. Runtjik joins the Tjik family in periwinkle with a pale pink
Command symbol. Zed Preview is electric periwinkle-blue (`#5685ff`); gold stays reserved for archived Nightly.

The preceding shared-identity pass remains in place:
Plex now uses a Hong Kong-centred blue globe with yellow continents and a small ivory play triangle in front. Its simplified public-domain Natural Earth coastlines are projected at 114.1694° E, 22.3193° N by `scripts/icons/plex-globe.py` (requires Shapely). Telegram is a paper plane with solid blue wings, a shaded central fold, matched rose-red
wing bands and narrow ivory companion stripes. Transmission retains its familiar form with a sharper
red handle. These sources feed the primary frameless theme and Homepage exports.

[Review Si Homepage's 14 frameless icons](../.local/icon-reviews/docs/rose-punk-homepage-review.html), including
original service illustrations and four shared desktop identities. All omit the
common tile and use the desktop study's optical sizing. Grimmory has its own
grimoire; Profilarr uses five mugshot portraits; Shelfmark is a ribbon bookmark.
Homepage assets and source configuration are prepared for a later deployment;
the live site has not been changed. `scripts/icons/homepage.json` keeps this
service inventory separate from the 106 desktop icons. The
[Homepage refinement review](../.local/icon-reviews/docs/rose-punk-homepage-coherence-review.html) compares
five further changes: calmer Seerr iris bands, more natural Profilarr faces and
shoulders, clearer Radarr/Sonarr markings and softer rose Scrutiny frames.
Frozen vectors, source hashes and rendered 24–96 px checks on dark and light
backgrounds live in `.local/icon-reviews/docs/assets/icon-homepage-coherence-review/`. Rebuild those
review artifacts with `python3 scripts/icons/homepage-coherence-review.py`
after `homepage.py` (Pillow, librsvg/PyGObject, pycairo and Fontconfig required).

The whole-set critique still flags Problem Reporting, Flatseal, Volume Control
and Tour as having more gloss than the reference. Sparse brand marks remain
intentional identity exceptions. Profilarr reads as a group at 24 px; individual
faces need roughly 48 px. Spotify’s lighter mint reduces white-mark contrast;
its three ivory waves are kept substantial. The annotated coherence review
includes every desktop icon at 64 and 24 px and frozen pre-pass server artwork.

Codex and Codex LB use filled wavy marks; Chezetc and Chezmoi use filled houses.
Hyprvoice retains Lucide audio-lines and oo7 retains Tabler fingerprint. Greetjik is
a custom Rainbow Dash-inspired rainbow mane, not an official project logo.
ChatGPT uses OpenAI knot geometry from Lobe Icons with an ivory backing.

Beekeeper Studio was uninstalled; DataGrip's application directory was already
absent and its stale launcher script and catalog artwork were removed. App data
and database connection settings were preserved. Azahar was subsequently uninstalled and removed from the catalog; its saved
data and settings were retained.


## Camera-led material pass

[Review the active catalog](../.local/icon-reviews/docs/rose-punk-material-review.html) or
[view the latest refinements](../.local/icon-reviews/docs/rose-punk-refinements.svg). The camera remains the
unchanged reference. The second pass removes decorative edge glints and inset
bevels, gives Bluetooth Adapters a blue body, makes Calendar taller, restores
Kitty's warm flat finish, and uses filled houses, a filled Collie face, and the
Codex wavy silhouette with prompt apertures. ChatGPT has an ivory backing within
its knot silhouette. Chrome, the disk-usage chart and Rust have new colour and
form treatments; ZapZap uses a handset bubble, Zoom its camera app symbol, and
Prowlarr a cute, freestanding tiger face.

The active set contains 106 icons. Thirteen retired or unused entries are removed
from the catalog, app mappings, aliases and current previews: Bluejay, Blender,
Bottles, Cheese, dconf Editor, Figma, Ghostty, GRASS GIS, HandBrake, Monochrome Music, NM GUI, Thunderbird and Zed Nightly. `scripts/icons/retired.json` preserves their
catalog and attribution records. Source artwork and historical snapshots are
archived, including the corrected cheese holes and cleaner bottles. They are
not active theme entries. QGIS remains for the retained Li application;
Codex remains a fleet identity even though its former desktop RPM was retired.

The current [style prompt](rose-punk-icon-style-prompt.md) takes precedence over
earlier palette and outline studies. Revised self-contained sources live in
`scripts/icons/local/`. `material_art.py` supplies other object illustrations and
details; `materials.py` shades retained geometry. Run `material-review.py` after
the existing rebuild commands to refresh comparisons and hashes.

Obsidian retains its upstream chipped-stone contour and four curved facets,
with rose, violet and periwinkle faces. The editable `local/obsidian.svg` replaces
the pointed crystal approximation and its disconnected highlight strokes;
the original reference and its hash remain in the provenance record.

## Maintenance

### Shared palette and shape review

[Open the color and icon review](../.local/icon-reviews/docs/rose-punk-color-review.html), or view the
[fleet overview](../.local/icon-reviews/docs/assets/icon-review/index.html). The review compares original app icons (packaged assets or upstream app marks,
with unchanged colors and geometry) with the current 106-icon set and previews
the 40 fleet labels. Original review references are archived locally in `.local/icon-reviews/docs/assets/icon-review/originals/`;
its `manifest.json` records each source and SHA-256. The generator verifies those
hashes and marks missing originals explicitly, without substituting earlier
Rose Punk artwork. A light backing keeps dark original marks visible.
Its eight symbol color families start with
`home/dot_config/vivid/themes/rose-punk.yml`. Shared `paint_overrides` in
`scripts/icons/palette.json` replace the old blue teal with mint teal
(`#46B6A2`, bright `#73D3B8`) across generated and hand-drawn icons. These
overrides affect icon artwork only; the terminal palette stays unchanged. Solid teal badges use dark inner marks for small-size contrast. Each family has a dominant color, highlight, shade and supporting
accent. This palette is used by the managed icon theme and runtime sprites.
Telegram uses solid blue wings, a shaded central fold, matched rose-red wing bands and narrow ivory companion stripes. Codex and Codex LB use the
filled wavy silhouette in violet and blue, with terminal-prompt apertures.

The review shows the palette, fleet icons and original-versus-themed app
comparison. The silhouette-choice section and its selection/export controls
have been removed. Historical reference downloads, licenses and hashes remain
in `scripts/icons/references/`.

Greetjik uses a custom Rainbow Dash-inspired rainbow mane: a swept forelock and
pointed trailing locks, with no face or body. Its six-color identity is a
deliberate exception to the single-family palette. Editable source artwork lives
in `scripts/icons/local/greetjik.svg`; provenance records the inspiration and the
previous Tabler horse identity. This is fan artwork, not an official project logo.

Use the size selector and Show originals toggle to compare the app set.
To rebuild the review offline:

```sh
python3 scripts/icons/palette-review.py
```

Assignments and archived shape choices live in `scripts/icons/palette.json`.
Generated review assets live under `.local/icon-reviews/docs/assets/icon-review/`.

### Current icon theme

Bartjik uses a magenta circular outline with a pale center dot; Notjik uses a
cyan rounded-square outline with a small rounded-square center. Tjikup uses the
same frame in amber with an up chevron. Runtjik uses periwinkle, a smaller pale
pink Command symbol, and the shared dark inset and material shading. Its theme
names are `runtjik` and `rose-punk-runtjik`; the on-demand launcher has no desktop
ID. Mailtjik keeps the dark rounded-square inset, adds white, blue and rose-red
airmail dashes around its border, and uses a white envelope flap inside. Greetjik is
a custom six-color rainbow mane.
Codex uses the wavy filled silhouette, centered within a 44-unit footprint.
Simple 24 px outline sources are placed at (8,8), sized 48 × 48 with source
stroke 2, yielding a 4 px stroke on the 64 px grid. Detailed brand geometry
retains its own internal proportions rather than receiving a blanket stroke.
Their editable 64 × 64 SVG sources are in `scripts/icons/local/`; `fullset.py`
preserves the identity geometry, removes the common tile, and applies optical
sizing through `frameless.py`. App-specific frames and backings remain.
The shared app catalog, gallery, and fleet terminal sprites include these icons.

Use ordinary theme icon names such as `bartjik` and `notjik`; Rose Punk aliases
stay inside its own theme. For direct SVG use, the generated
assets live in `home/dot_local/share/icons/rose-punk/scalable/apps/`.
After editing their source SVGs, run `fullset.py`, `gallery.py`, and
`build-fleet.py` to refresh the catalog assets and terminal sprites.

The [reusable design prompt](rose-punk-icon-style-prompt.md) describes the visual
language and how to add icons. Source geometry, hashes and attribution are in
`scripts/icons/upstream/`, `catalog.json` and `provenance.json`. Upstream license
texts are bundled beside the SVGs. These are unofficial themed application
marks; app identities and trademarks remain with their respective owners.

```sh
python3 scripts/icons/fullset.py       # deterministic offline rebuild
python3 scripts/icons/build-fleet.py   # terminal sprites
python3 scripts/icons/gallery.py       # catalog and contact sheets
python3 scripts/icons/palette-review.py # comparison and shape-reference review
python3 scripts/icons/material-review.py # frozen before / current material comparison
python3 scripts/icons/frameless-review.py # primary frameless review and SVG download
python3 scripts/icons/homepage.py       # frameless Si service icons, no deployment
python3 scripts/icons/audit.py         # report uncovered local launcher entries
python3 -B -m unittest discover -s tests -p 'test_rose_punk_icons.py' -v
```

Chezmoi deploys **Rose Punk** under the directory ID `rose-punk`. The old
outline study is archived in `scripts/icons/archive/outline/`, outside the
managed icon tree. Rose Punk inherits Neuwaita, Adwaita and hicolor for icons
it does not provide. The installer migrates settings that still select
`rose-punk-illustrated` to `rose-punk`, preserving other theme choices.

Application launchers use ordinary upstream icon names. Rose Punk supplies
aliases inside its own theme directory; it does not install its artwork into
hicolor or force `rose-punk-*` names into desktop entries. Vendor icons in
hicolor remain available as the original fallback when another theme is chosen.

The client apply hook runs `scripts/icons/install.py` to migrate old overrides
and refresh caches. It removes only hicolor symlinks that point into the
Rose Punk themes. It restores recorded launcher overlays, preserves edited
launch commands, and changes only Icon fields in managed native launchers.
Unresolved edited overrides are preserved and reported for review. Recovery
records live in `~/.local/state/rose-punk-icons/`; `theme-switch-backups.json`
contains launcher contents from before migration. `--restore` remains an alias
for this cleanup. There is no blanket deletion of user icon files.

Installation and ordinary apply do **not** select a theme. Managed GTK3/GTK4
files preserve the existing icon-theme setting, dconf does not pin one, and
Qt6ct is changed only by an explicit selection:

```sh
python3 scripts/icons/choose.py          # select Rose Punk
python3 scripts/icons/choose.py Neuwaita # switch to another installed theme
python3 scripts/icons/install.py        # migrate/refresh; retain that choice
python3 scripts/icons/check-theme.py    # report overrides and missing fallbacks
```

Desktop settings applications can also select themes normally. Absolute icon
paths supplied by applications can bypass theme lookup; `check-theme.py` reports
these instead of silently rewriting launchers. Missing upstream/PWA fallback
icons should be repaired individually, without putting Rose Punk artwork back
into hicolor.

Tjikup notifications request the `tjikup-notification` icon by name. Its original
fallback PNG belongs to the Tooltjik installer. `build-fleet.py` writes only
terminal sprites and does not generate a PNG in the managed icon tree. Inline terminal sprites are a separate presentation layer,
not desktop icon-theme lookup.

For focused setup deployment, apply the available `index.theme` files, managed desktop
entries, GTK3/GTK4 settings and the dconf interface file, then run `install.py`.
No full desktop apply, artwork rebuild, or package update is required. Run
`python3 -B -m unittest discover -s tests -p 'test_icon_theme_setup.py' -v` for
isolated migration and preference-preservation tests.

## Primary frameless set and secondary framed build

[Review all 106 primary frameless icons](../.local/icon-reviews/docs/rose-punk-icons-frameless.html),
[view the contact sheet](../.local/icon-reviews/docs/rose-punk-icons-frameless.svg), or
[download their SVGs](../.local/icon-reviews/docs/assets/icon-frameless-review/rose-punk-frameless.zip).
The managed `rose-punk` directory contains the frameless originals and uses
the display name **Rose Punk**. `fullset.py`
builds them; galleries, fleet sprites and shared Homepage identities consume
those originals. `frameless-review.py` exports them without changing their
artwork. Its `framed/` assets are frozen historical comparison snapshots.

Only the common `tile` is removed. App-specific borders, backings, colours and
geometry remain. Uniform scaling and centering use rendered alpha bounds on the
64 × 64 canvas, targeting 2,200 square units of alpha coverage with the longest
dimension constrained to 50–56 units. The review offers 24–128 px sizes and dark,
plum, light and checkerboard backgrounds. PyGObject/librsvg, pycairo and Pillow
are required for optical sizing and review rendering.

**Rose Punk Framed** will have directory ID `rose-punk-framed`, the same catalog,
ordinary app aliases and Rose Punk aliases, and the same Neuwaita/Adwaita/hicolor
fallbacks. It is prepared in `scripts/icons/framed.py`. No secondary theme or
approval record is created until final frameless sign-off, so an unfinished
empty theme does not appear in settings. Ordinary builds never approve artwork
or regenerate the secondary set.

After final visual approval of the frameless originals, record that sign-off
and generate the secondary set:

```sh
python3 scripts/icons/framed.py approve # only after final frameless sign-off
python3 scripts/icons/framed.py build
```

`approve` records the SHA-256 of every primary SVG and the exact aliases in
`scripts/icons/frameless-approved.json`. `build` checks this record before
writing anything; any artwork, catalog membership or alias change requires
review and a new sign-off. `python3 scripts/icons/framed.py status` reports
whether the current set matches approval. Sign-off is currently pending.

The framed builder preserves every artwork node and paint. It adds one outer
uniform scale of 6/7, fitting the frameless maximum extent of 56 units to 48,
centered at the tile's (32, 31) center. It then adds the existing flat tile:
x=3, y=2, width=58, height=58, radius=17, fill `#26233a`, outline `#555169` at 45%
opacity and 0.65 units. It never redraws the symbol or derives it from the old
framed snapshots. Review the resulting framed set for final sizing acceptance.

Build outputs are the complete managed secondary theme, an installable ZIP at
`.local/icon-reviews/docs/assets/icon-framed/rose-punk-framed.zip`, and a manifest in the same folder
recording each input/output hash, the approval hash and frame parameters. The
ZIP includes `index.theme` and regular SVG copies for all aliases; extract its
`rose-punk-framed/` directory under `~/.local/share/icons/` to install directly.
Chezmoi can instead deploy the generated managed theme and its symlink aliases.
Run `install.py` after deployment to refresh caches; select explicitly with
`python3 scripts/icons/choose.py 'Rose Punk Framed'`. The default selection stays
Rose Punk. Generating assets does not deploy them or change the selected theme.

```sh
python3 -B -m unittest discover -s tests -p 'test_icon_frameless.py' -v
python3 -B -m unittest discover -s tests -p 'test_icon_framed.py' -v
```
