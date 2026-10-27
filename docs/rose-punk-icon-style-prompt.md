# Prompt for additional Rose Punk illustrated icons

Icon galleries, comparison snapshots and rendered previews are local review
artifacts under `.local/icon-reviews/docs/`, which Git ignores. They are
not required to build or deploy icons. The links below open that local archive.

Use the [camera](../.local/icon-reviews/docs/assets/icon-material-review/before/camera.svg) as the primary
reference for detail, material, proportions and restraint. The
[before/after review](../.local/icon-reviews/docs/rose-punk-material-review.html) shows the current pass;
the [study sheet](../.local/icon-reviews/docs/rose-punk-material-study.svg) collects representative objects.

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
> approved frameless original, with one uniform sizing transform and the shared
> flat tile. Do not independently redraw or recolour a second framed original.
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
> `#b39bd9` and `#df77ac`, with warm ivory `#fff0da` and cool ink `#34304f`.
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

The active catalog contains 107 apps and services. `scripts/icons/retired.json`
archives 13 retired/unused entries; do not add them back when making a new study.
Their source artwork and frozen snapshots are historical, not active choices.
The revised clean forms are self-contained in `local/*.svg` with
`data-material="authored"`, so the generic shading pass does not reintroduce the
rejected glints or bevels. `rose-punk-refinements.svg` shows the active revisions.
Codex uses the attributed Lobe Icons vector in `upstream/codex-lobe.svg`.

## Google family, Herdr and Brave

Interpret Google products as filled objects and forms in the shared palette:
Gmail's folded envelope, Calendar's bound page, Photos' four-petal pinwheel and
Chrome's interlocking blades with a blue glass centre. Keep distinguishing
geometry and warm/cool colour separation at small sizes. Herdr is a solid
timber fence with painted rails. Brave's original lion paths use copper/ochre
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

## Secondary set after sign-off

Finish and visually approve the primary frameless set first. Then use
`python3 scripts/icons/framed.py approve` and `python3 scripts/icons/framed.py build`.
The builder locks original SVG hashes and aliases, adds the existing flat plum
tile and a uniform 6/7 sizing transform, and emits **Rose Punk Framed** as a
complete secondary theme and ZIP. Changes to the originals invalidate sign-off.
See [the maintenance guide](rose-punk-icons.md#primary-frameless-set-and-secondary-framed-build).
