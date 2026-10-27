# Prompt for additional Rose Punk illustrated icons

Use this prompt with an SVG-capable designer or image model. Replace the bracketed fields and attach the official app icon plus a few finished icons from this repository.

> Create an illustrated Rose Punk desktop icon for **[APP NAME]**.
>
> **Identity reference:** [OFFICIAL ICON / SVG / URL]. Preserve the distinctive silhouette, internal negative spaces and identifying object of this application. Recognition is more important than novelty. Do not invent an abstract substitute, generic animal face, initials badge or unrelated symbol. Match the official fox-and-globe for Firefox, mole for Mullvad, bird-and-envelope for Thunderbird, Wilber-and-brush for GIMP, and download-tray identity for Transmission.
>
> **Style references:** [three finished icons from `home/dot_local/share/icons/rose-punk-illustrated/scalable/apps/`]. Match their size, lighting, outline weight, material and contrast.
>
> **Canvas:** square, 64 × 64 design grid; scalable SVG preferred. Transparent outside the tile. The tile occupies x=3..61, y=2..60, with a 17-unit corner radius and a subtle shadow extending to y=62. Keep the main symbol around x=9..55 and y=8..54, optically centered. No scenery, ground plane, label, decorative sparkles or badge added to the logo.
>
> **Material:** raised enamel illustration on a dark plum tile. Soft upper-left highlights, restrained lower-right relief shadow, simple layered shapes. Avoid photorealism, fuzzy bloom, excessive texture or glossy plastic. Do not flatten all detail into an outline: this is the filled illustrated direction.
>
> **Palette:** tile gradient `#44304e` → `#2d233e` → `#211d32`; rose enamel `#f4c8d7` → `#e88bb6` → `#b94e87`; lilac accents `#d9c3f2`, `#b39bd9`, `#9272ba`; pale highlight `#f4b7c9`; dark internal detail `#35213f` / `#482b53`; shadow `#100d1c`. Preserve light/dark separation from the reference. Use rose for the primary identity, lilac for secondary components, dark plum for important negative spaces. Avoid retaining unrelated bright brand colors.
>
> **Legibility:** recognizable at 24, 32 and 48 px, not just enlarged. Keep essential eyes, beaks, tails, apertures and brush shapes clear. Avoid tiny lettering. Thin highlights must not erase the logo or become noise. Match optical weight to the reference set.
>
> **Deliverable:** one self-contained editable SVG, no embedded raster image, no external resources, no scripts, no text rendered with an unavailable font. Retain upstream attribution and license when adapting existing SVG geometry. Supply a 32 px and 64 px preview on `#191724` for review.

## Repository integration

1. Add the source SVG to `scripts/icons/upstream/`, retaining its original geometry, attribution and license. Record its origin and SHA-256 in `provenance.json`. For original artwork, add editable paths to `extra_art.py`.
2. Add the app to `catalog.json` and its desktop IDs to `apps.json`. Use `mode: brand` for clean logo geometry, `illustration` for a detailed SVG with shades to remap, or `original` for authored paths. Supply all canonical icon names and common desktop variants.
3. Run `python3 scripts/icons/fullset.py` and `python3 scripts/icons/gallery.py`. The builder writes artwork and theme aliases; it never needs the network or installed upstream theme files after sources are vendored.
4. Inspect the actual rendered icon at 24/32/48/64 px. Compare against the official app icon. Reject unrecognizable simplifications, unresolved image placeholders, low contrast, clipped geometry and stray brand colors.
5. Run `python3 -B -m unittest discover -s tests -p 'test_rose_punk_icons.py' -v` and `python3 scripts/icons/audit.py`. Deploy through Chezmoi/Tjikup, or use the focused commands in the maintenance guide.

The built-in image generator was unavailable during this set's creation. These deliverables use editable vector artwork and attributed upstream SVG geometry; no generated raster images are required.
