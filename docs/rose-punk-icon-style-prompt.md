# Prompt for additional Rose Punk illustrated icons

Icon galleries, comparison snapshots and rendered previews are local review
artifacts under `.local/icon-reviews/docs/`, which Git ignores. They are
not required to build or deploy icons.

Use the frozen camera reference as the primary reference for detail, material,
proportions and restraint. Local before/after reviews and study sheets provide
supporting comparisons; keep their links out of the docs.

> Create an illustrated Rose Punk desktop icon for **[APP NAME]**, using
> **[OFFICIAL ICON / SOURCE]** to preserve its identifying silhouette and internal
> negative spaces. Match the supplied camera's level of stylization: a small,
> believable object with useful surface detail, clear proportions and soft depth.
>
> **Canvas and scale:** editable SVG on a transparent 64 × 64 grid. Frameless
> **Rose Punk** is the primary set. Omit the common plum tile; retain borders,
> circles and backings that belong to the app identity. Preserve natural
> proportions and balance visible artwork to a 50–56 unit longest dimension,
> with at least four units of margin. Do not stretch silhouettes into a square.
> Bartjik retains its circular identity; Codex retains its wavy filled silhouette
> and terminal-prompt apertures. **Rose Punk Framed** is derived later from the
> approved frameless original, with a maintained per-icon optical scale and position from
> `scripts/icons/framed-layout.json`, and the shared flat tile. Use one isotropic
> transform per icon; aliases inherit their canonical icon’s layout. Do not independently redraw or recolour a second framed original.
>
> **Materials:** make details describe the object. Camera glass has layered
> optical rings, cool depth and a few soft reflections. Magnifying glass remains
> translucent. Rubber grips have fine perforations; fabric has a restrained
> weave; paper has thickness, folds and page edges; metal has narrow highlights
> and a cooler underside. Use authored paths, subtle gradients and selective
> texture. Do not add arbitrary white glints, inset rims or a raised panel effect.
> Use clean pigment colours on bottles and hardware. Prefer filled objects over
> generic outline drawings; preserve deliberate flat treatments such as Fonts,
> Kitty and Bluetooth Manager. A logo can remain simpler than a physical object. Keep the transparent background clear. Avoid global noise, forced bevels, duplicate offset silhouettes,
> ground shadows, decorative sparkles and photographic gloss.
>
> **Colour:** Rose Punk is the starting point, not a fixed colour limit. Use the
> imaginative desert and cosmic colour relationships of Jodorowsky's Dune as a
> broad palette cue: warm sand and amber, copper and coral, jade and turquoise,
> indigo, violet and rose. Choose colours for the icon's subject and materials.
> Useful pigments include `#e6ae62`, `#dd795f`, `#46b6a2`, `#65b9c8`, `#8596ed`,
> `#b39bd9` and `#df77ac`, plus sun-yellow `#f6cf58` for bright focal marks, with warm ivory `#fff0da` and cool ink `#34304f`.
> Use multiple coordinated accents where they explain different parts. Preserve
> recognizable brand structure and the Zed Stable/Preview distinction. Telegram
> keeps its blue wings and rose-red/ivory bands; Codex uses filled violet and blue variants.
>
> **Small-size quality:** inspect at 24, 32, 48, 64 and 96 px. The main silhouette
> and important negative spaces must read before the texture. Small detail can
> disappear gracefully; it must not make the icon muddy. Protect dark marks on
> coloured surfaces. Never use object-bounding-box gradients on perfectly
> vertical or horizontal strokes; give those explicit user-space coordinates.
>
> **Light surfaces:** essential unbacked shapes must also read on off-white and
> white. Preserve the original ivory/gold/blue Zed channel colours and Zen's
> rose/blush/ivory rings; use dark plum fills behind those marks so the bright
> pigments remain intact. Unbacked Signal and Nginx use deeper periwinkle and
> jade pigments. Check the same artwork on plum and dark backgrounds at 24, 32
> and 64 px. Target 3:1 pigment contrast against the actual adjacent surface,
> including an icon's own dark fill; do not dull every colour to meet contrast
> against a surface it no longer touches.
>
> **Deliverable:** one self-contained editable SVG, no embedded raster image,
> scripts, external resources or font-dependent text. Preserve attribution and
> licenses for adapted upstream geometry. Include a small-size preview and a
> comparison with the unchanged camera reference.

## Repository integration

- Existing identity sources live in `scripts/icons/local/` and
  `scripts/icons/upstream/`; the catalog and provenance retain their mappings.
- `scripts/icons/material_art.py` contains the first-pass object illustrations and
  object-specific detail overlays. Its registry deliberately supersedes the
  former simple geometry for those objects; it does not rewrite vendored
  upstream sources. Add object-specific material work here.
- `scripts/icons/materials.py` supplies continuous pigment mapping and surface
  ramps for retained shapes. The camera bypasses material shading; shared frameless sizing still applies.
  `palette.json` remains the family assignment and paint-override source;
  material highlights and secondary pigments extend beyond the terminal palette.
- `scripts/icons/fullset.py` combines these layers and outputs the primary frameless theme. Rebuild the downstream assets:

```sh
python3 -B scripts/icons/release.py build
python3 -B scripts/icons/release.py check
# Optional local visual reviews (some require historical snapshots):
python3 scripts/icons/gallery.py
python3 scripts/icons/frameless-review.py
python3 -B -m unittest discover -s tests -p 'test_*icon*.py' -v
```

The `before/` assets in `.local/icon-reviews/docs/assets/icon-material-review/` are frozen review
snapshots, not upstream originals and not build inputs. Do not overwrite them
when rebuilding. `manifest.json` records before/after hashes and the treatment
for each icon. The unchanged upstream originals and their licenses remain in
the original-icon review. Deployment is separate from generating the review.

## Active scope and revision 2

The active desktop catalog contains 142 entries. Together with the distinct
Homepage services and Fish shell, the seven accepted review batches cover 167
icons. `scripts/icons/retired.json` archives retired/unused entries; do not add
them back when making a new study. Their sources remain historical inputs.
Accepted normalized revisions live in `local/reviewed/*.svg` with the
`reviewed-svg` build mode: verify provenance and preserve their exact bytes,
without another shading or sizing pass. `review-selections.json` records all
167 final decisions, including the 24 unchanged originals. Chezmoi and Chezetc
share cyan/red house geometry in System and hardware, outside Tjik.
Codex uses the attributed Lobe Icons vector in `upstream/codex-lobe.svg`.

Review numbering follows `display_sections` in `review-selections.json`: TjikOS
comes first, with Greetjik at number 1, Gmailtjik second-last and Mailtjik last.
Terminal Apps, Brand Marks - Solid and Brand Marks - Open follow, then Starfix
and Craft, then Everyday desktop, System and hardware, Media and graphics,
and Developer tools. Starfix tags the media and
library service suite; icons already shown as brand marks are not repeated
in the full review.
`original_review_number` retains earlier batch references; provenance review
numbers remain historical. Category tags overlap and follow the current order.
Fish shell follows Kitty in Terminal Apps. Its approved icon shares Kitty’s
flat treatment: a jade fish silhouette, mint contour and one dark chevron fin.
Keep it free of eyes, separate fins and gradients. Within Craft, the Adobe-style
creative apps precede WordCraft, DeckCraft and GridCraft; FigCraft, CADCraft
and Craft Anything follow the office-style group.

## Google family, Herdr and Brave

Interpret Google products as filled objects and forms in the shared palette:
Gmail's folded envelope, Calendar's bound page, Photos' four-petal pinwheel and
Chrome's interlocking blades with a blue glass centre. Keep distinguishing
geometry and warm/cool colour separation at small sizes. Herdr uses the terminal family shell with a proposed three-pane agent-runtime
mark, based on its persistent terminals and pane status. Brave's original lion paths use copper/ochre
pigment and an ivory face; avoid pale pink-on-white that washes out the mark.

## Material consistency pass

Concentrate detail in one focal feature per icon. Camera's grip texture, lens
rings and glass reflections each explain a material; use the same discipline for
book bindings, archive zippers, screen glass and metal hubs. Keep supporting
surfaces quiet. Avoid generic diagonal shine, inset highlight frames and global
bevels. Preserve familiar app geometry and the natural proportions of objects.

Photo viewers share ivory frames, blue skies, mint landscapes and restrained
cyan glass. Functional marks remain legible at 24 px; secondary texture should
recede at that size. Keep colour in shadows instead of muddy grey or brown.
Simple brand marks can remain simple. Do not add texture or highlights merely
to match the number of details in Camera.

## ArtCraft family consistency

FilmCraft's cleaned owl is the user-selected geometry and shading reference for
the fifteen Craft apps. Preserve its geometry and shading structure; the family
finish pass brightens its facial ivory together with its siblings. The frozen
camera remains the unchanged overall Rose Punk material reference.

Craft whites use bright warm ivory `#fffaf2`, with restrained cool side shading
where pale forms meet a light canvas. Avoid enclosing contour strokes: use
filled colour boundaries and physical edge thickness. Retain functional lines
such as mouths, drafting guides, grid divisions and feather marks.

Use continuous filled contours, balanced curves and deliberate negative spaces.
Keep bilateral features aligned where the subject is frontal; preserve the
natural profiles and distinctive silhouettes of the other animals. A single
main ramp and one or two quiet supporting planes should carry the form. Use
clear dark eyes, with restrained amber irises where the size permits. Reserve
small curved marks for meaningful feathers or fur, and omit decorative glints,
fine hatching and fragmented polygon shading.

The shared Craft ramps in `material_art.py` follow the owl's broad shading.
Ivory objects may use a fine plum edge to remain visible on light surfaces;
coloured animal silhouettes do not need a global outline. WordCraft, GridCraft
and CADCraft share paper treatment, fine edges and consistent functional line
weights; DeckCraft uses filled hardware surfaces. The fox's tail fan, the
lion's full mane, the zebra's stripes and each tool's functional marks remain
part of their identities. Review the family together at 24, 32, 48, 64 and 96 px.

The owl remains the accepted reference. The fourteen sibling revisions were
accepted for `0.1.0-rc.13`; the explicit release cut authorizes deriving its
framed counterpart from the same approved SVGs and maintained optical layouts.

## Secondary set after sign-off

Finish and visually approve the primary frameless set first. Then use
`python3 scripts/icons/framed.py approve` and `python3 scripts/icons/framed.py build`.
The builder locks original SVG hashes and aliases, adds the existing flat plum
tile and reviewed per-icon scales/offsets from `framed-layout.json`, and emits
**Rose Punk Framed** as a
complete secondary theme and ZIP. Changes to the originals invalidate sign-off.
See [the maintenance guide](rose-punk-icons.md#primary-frameless-set-and-secondary-framed-build).

## Terminal applications

Lazygit's terminal shell is the default for terminal-app identities: a plum
`#34304f` rounded rectangle at `(7,9)`, `50 × 46`, radius `7` on the 64-unit
canvas, with the ivory prompt at the upper left. Bottom uses a dotted activity
trace; Vivid uses a finer branching color tree. Preserve individual application
marks within that shared shell rather than replacing them with a generic prompt.
Sun-yellow is recorded as `pigments.sun-yellow` in `palette.json`; protect it
with ink when the identity otherwise disappears against light backgrounds.

## Freshness and edge consistency

Use `#fff0da` for the functional foreground marks in Mailtjik, Gmailtjik,
Synctjik, Runtjik, Notjik and Tjikup. Bartjik keeps its deliberately blush
centre. Paper uses a lighter warm highlight (`#fff8ec`) and a shallow warm
shadow (`#f8ecda`); avoid grey-violet shading across the main paper face.
Metal can use cool blue highlights. These material highlights are distinct
from the shared foreground ivory. Keep shadows coloured and supporting
surfaces quiet; preserve Camera as the unchanged material reference.

Simple logos follow the majority filled-silhouette treatment. Avoid added
hairline outlines and offset shadow copies; preserve borders and dark
backings that belong to an identity, including the Zed channel backings.
Use visible coloured fills for exposed logo shapes rather than pale fills
that need an added keyline. Strata's upper ribbon is rose; Steam's exposed
link is blue. Paper edges and physical part boundaries remain material detail.

Gitfetch and uuctl use Lazygit's terminal shell and ivory prompt. Gitfetch
combines a copper branch with jade statistics; uuctl uses control sliders.
Keep each application mark distinct inside the shared shell.

## Object construction and review categories

Use Camera, Disk Usage Analyzer, Tweaks and Document Scanner as the material
references for this pass. Give objects a focal material feature: wound tape
layers, cut key teeth, machined platter rings, a real zipper pull aperture,
raised keycaps, book binding or folded folder gussets. Use coordinated colours
for different physical parts. Flatseal keeps its upstream reel geometry with an ivory tape face,
jade side thickness and only two faint winding lines; Volume Control keeps its concentric arc and dial relationship.
Google Calendar is an exact blue-header variant of Calendar.

Review categories are overlapping tags. Craft contains all 15 Craft identities;
Media contains Video Player and related media tools. Ephemera belongs to Brand
Marks - Open. Gmail, Bun, Brave and all three Zed variants appear in Brand
Marks - Solid, alongside Color Profile Viewer, Python, Steam and Telegram.
Category moves do not remove icons from the full catalog.

The construction review favours legible parts over extra detail: keys retain their newer gold and jade geometry, with the steel ring passing behind
the upper heads and through both holes into a foreground lower arc; the rotary dial face stays light,
and keyboard caps do not have overlapping shadow blocks. Archive zipper teeth
are secondary to a coherent slider and open pull. Contacts uses a direct ivory
portrait on its bound cover. Herdr keeps three clean panes without tiny symbols.
