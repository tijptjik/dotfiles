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

Chezmoi deploys the SVGs and aliases. Its client-only `run_after_40-rose-punk-icons`
hook installs desktop overrides and refreshes caches; Tjikup includes this in
its hook schedule. Original main `Icon` fields are replaced with unique
`rose-punk-*` names, preserving Exec, actions and other desktop metadata.
Aliases for original icon names also cover Hamr's stored recent system entries.
The illustrated theme inherits Neuwaita, Adwaita and hicolor for unrelated icons.

For focused deployment:

```sh
chezmoi apply --include=files,dirs,symlinks ~/.local/share/icons/rose-punk-illustrated ~/.local/share/icons/hicolor/scalable/apps
python3 scripts/icons/install.py
python3 scripts/icons/choose.py b
systemctl --user restart hamr-daemon.service hamr-gtk.service
```

The original 25-app outline study is retained as an archive. `choose.py a` can
still select it, but only the illustrated direction receives complete coverage.
The chosen theme is saved in the managed GTK4 and dconf settings.

Installer-created desktop overrides retain recovery data under
`~/.local/state/rose-punk-icons/desktop-overrides.json`. `install.py --restore`
restores only entries unchanged since installation. Full retirement also
requires reverting managed Icon fields and disabling the apply hook, otherwise
the next apply reinstates the theme.
