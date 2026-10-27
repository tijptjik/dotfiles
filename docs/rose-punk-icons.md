# Rose Punk illustrated application icons

The selected illustrated direction covers **127 Hamr desktop IDs**, grouped into
**102 installed app families**, plus **10 additional widely used apps**. The
coverage audit follows Hamr's inclusion rules, including user, system and
Flatpak desktop directories. Hidden/NoDisplay entries are excluded. Alternate
versions and duplicate desktop entries share one family icon.

[Browse the searchable full catalog](rose-punk-icons-gallery.html), with previews
from 24 to 96 px. [Review the five identity redraws](rose-punk-icons-redrawn.svg).
Printable contact sheets: [1](rose-punk-icons-catalog-1.svg),
[2](rose-punk-icons-catalog-2.svg), [3](rose-punk-icons-catalog-3.svg),
[4](rose-punk-icons-catalog-4.svg).

Firefox, Mullvad, Thunderbird, GIMP and Transmission now use authentic upstream
logo geometry, replacing the unrecognizable earlier interpretations. Colors,
tile shape and relief treatment follow the illustrated Rose Punk direction.
Other illustrations preserve their app's visual identity while remapping its
colors to the same rose/plum/lilac palette.

The ten extras are **VS Code, Slack, Microsoft Teams, Notion, Figma, Microsoft
Edge, Blender, Inkscape, LibreOffice and Audacity**. They were absent from the
local launcher inventory. This is a practical widely used selection for broader
coverage, not a measured global top-ten ranking. Artwork and aliases are
installed; the applications themselves are not installed.

## Maintenance

The [reusable design prompt](rose-punk-icon-style-prompt.md) describes the visual
language and how to add icons. Source geometry, hashes and attribution are in
`scripts/icons/upstream/`, `catalog.json` and `provenance.json`. Upstream license
texts are bundled beside the SVGs. These are unofficial themed application
marks; app identities and trademarks remain with their respective owners.

```sh
python3 scripts/icons/fullset.py       # deterministic offline rebuild
python3 scripts/icons/gallery.py       # catalog and contact sheets
python3 scripts/icons/audit.py         # report uncovered local launcher entries
python3 -B -m unittest discover -s tests -p 'test_rose_punk_icons.py' -v
```

Chezmoi deploys a named theme displayed as **Rose Punk**. Its stable directory ID
is `rose-punk-illustrated`; keeping that ID avoids relocating artwork while it
is being refined. The old outline study is hidden from theme selectors and is
labelled `Rose Punk (Outline archive)`. Rose Punk inherits Neuwaita, Adwaita and
hicolor for icons it does not provide.

Application launchers use ordinary upstream icon names. Rose Punk supplies
aliases inside its own theme directory; it does not install its artwork into
hicolor or force `rose-punk-*` names into desktop entries. Vendor icons in
hicolor remain available as the original fallback when another theme is chosen.

The client apply hook runs `scripts/icons/install.py` to migrate old overrides
and refresh caches. It removes only hicolor symlinks that point into the two
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
fallback PNG belongs to the Tooltjik installer; the generated Rose Punk PNG is
not deployed over it. Inline terminal sprites are a separate presentation layer,
not desktop icon-theme lookup.

For focused setup deployment, apply the two `index.theme` files, managed desktop
entries, GTK3/GTK4 settings and the dconf interface file, then run `install.py`.
No full desktop apply, artwork rebuild, or package update is required. Run
`python3 -B -m unittest discover -s tests -p 'test_icon_theme_setup.py' -v` for
isolated migration and preference-preservation tests.
