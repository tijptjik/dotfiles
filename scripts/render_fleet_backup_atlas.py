#!/usr/bin/env python3
"""Render the documented fleet policy as an editable, self-contained SVG.

Run from any directory. Optional PNG rendering requires CairoSVG:
    python scripts/render_fleet_backup_atlas.py --png
This is a documentation renderer; it does not inspect or change live services.
"""

import argparse
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/fleet-backup-atlas.svg"
INK = "#182C40"
MUTED = "#576B7D"
BLUE = "#286CC4"
GREEN = "#137B67"
PURPLE = "#8054AF"
AMBER = "#9A6511"
TEAL = "#207A90"
PARTS = []


def text(x, y, value, size=18, color=INK, weight=400, anchor="start"):
    PARTS.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
                 f'font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')


def rect(x, y, width, height, fill="#FFFFFF", stroke="#DEE6ED", radius=16):
    PARTS.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                 f'rx="{radius}" fill="{fill}" stroke="{stroke}"/>')


ICONS = {
    "desktop": '<rect x="3" y="4" width="26" height="18" rx="2"/><path d="M16 22v6m-7 0h14"/>',
    "laptop": '<rect x="6" y="5" width="20" height="17" rx="2"/><path d="M6 22l-4 5h28l-4-5M12 25h8"/>',
    "disk": '<rect x="5" y="3" width="22" height="26" rx="3"/><circle cx="16" cy="14" r="6"/><path d="M16 14l5-4M9 25h1m4 0h1"/>',
    "server": '<rect x="4" y="3" width="24" height="11" rx="2"/><rect x="4" y="18" width="24" height="11" rx="2"/><path d="M9 8h1m5 0h8M9 23h1m5 0h8"/>',
    "pool": '<ellipse cx="16" cy="6" rx="12" ry="4"/><path d="M4 6v9c0 5 24 5 24 0V6M4 15v10c0 5 24 5 24 0V15"/>',
    "shield": '<path d="M16 2L4 7v10c0 7 12 13 12 13s12-6 12-13V7zM10 15l4 4 8-9"/>',
    "cloud": '<path d="M8 25a7 7 0 0 1-1-14 9 9 0 0 1 18-1 8 8 0 0 1 0 15z"/>',
    "drive": '<path d="M12 3h9l10 18-5 8H6l-5-8zM12 3l14 26M21 3L6 29M1 21h30"/>',
    "photo": '<rect x="3" y="4" width="26" height="24" rx="3"/><circle cx="11" cy="12" r="3"/><path d="M4 25l8-7 5 4 6-9 6 12"/>',
    "key": '<circle cx="11" cy="11" r="7"/><path d="M16 16l13 13m-5-5 4-4m-9-1 4-4"/>',
    "git": '<circle cx="8" cy="6" r="3"/><circle cx="8" cy="26" r="3"/><circle cx="25" cy="8" r="3"/><path d="M8 9v14m17-12c0 10-17 4-17 12"/>',
    "archive": '<rect x="3" y="4" width="26" height="7" rx="1"/><path d="M5 11v17h22V11M12 17h8"/>',
    "backup": '<path d="M5 10A12 12 0 1 1 4 21M5 3v7h7M16 8v9l6 3"/>',
    "code": '<path d="M10 8l-8 8 8 8m12-16 8 8-8 8M19 3l-6 26"/>',
    "folder": '<path d="M2 8h11l3 4h14v16H2zM2 8V4h11l3 4h12v4"/>',
    "download": '<path d="M16 2v19m-7-7 7 7 7-7M3 23v6h26v-6"/>',
    "media": '<rect x="3" y="3" width="26" height="26" rx="3"/><path d="M12 9l11 7-11 7z"/>',
    "assets": '<path d="M16 2l13 7v14l-13 7-13-7V9zM3 9l13 7 13-7M16 16v14M9 6l14 7"/>',
    "config": '<path d="M5 2v28M16 2v28M27 2v28"/><rect x="2" y="8" width="6" height="6" fill="white"/><rect x="13" y="20" width="6" height="6" fill="white"/><rect x="24" y="5" width="6" height="6" fill="white"/>',
    "mail": '<rect x="2" y="5" width="28" height="22" rx="3"/><path d="M3 7l13 11L29 7"/>',
    "document": '<path d="M6 2h13l7 7v21H6zM19 2v8h7M11 16h10M11 22h10"/>',
}


def icon(name, x, y, color=BLUE, scale=1):
    PARTS.append(f'<g transform="translate({x} {y}) scale({scale})" fill="none" '
                 f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
                 f'stroke-linejoin="round">{ICONS[name]}</g>')


def place(x, y, kind, identifier, label, note, color=BLUE):
    icon(kind, x, y, color, 1.2)
    text(x + 52, y + 16, f"{identifier}  {label}", 21, INK, 650)
    text(x + 52, y + 42, note, 16, MUTED)


def arrow(x1, x2, y, label, color=GREEN, both=False, dashed=False):
    dash = 'stroke-dasharray="7 5"' if dashed else ""
    direction = 1 if x2 > x1 else -1
    PARTS.append(f'<path d="M{x1} {y}H{x2}" stroke="{color}" stroke-width="2.5" '
                 f'fill="none" {dash}/><path d="M{x2-8*direction} {y-5}l{8*direction} 5 {-8*direction} 5" '
                 f'fill="none" stroke="{color}" stroke-width="2.5"/>')
    if both:
        PARTS.append(f'<path d="M{x1+8} {y-5}l-8 5 8 5" fill="none" '
                     f'stroke="{color}" stroke-width="2.5"/>')
    text((x1 + x2) / 2, y - 12, label, 15, color, 650, "middle")


def node(x, y, kind, title, subtitle, color=BLUE):
    icon(kind, x, y + 4, color)
    text(x + 44, y + 18, title, 21, INK, 650)
    text(x + 44, y + 43, subtitle, 16, MUTED)


def lane(y, number, title, note):
    rect(40, y, 1720, 132)
    text(62, y + 31, number, 15, BLUE, 700)
    text(105, y + 31, title, 20, INK, 650)
    text(1736, y + 31, note, 16, MUTED, anchor="end")


def render():
    PARTS.clear()
    PARTS.append('<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="2140" '
                 'viewBox="0 0 1800 2140" role="img" aria-labelledby="title desc">'
                 '<title id="title">Fleet storage atlas: devices, content and recovery routes</title>'
                 '<desc id="desc">Fi desktop and its secondary SSD, Li laptop, Si server with '
                 'storage and parity, Google Drive and Photos, Cloudflare, Git and Bitwarden. '
                 'Six lanes distinguish synchronization, snapshots, copies, archives, parity '
                 'and deployment. Cloudflare backups run weekly to Fi; Google Drive archives '
                 'and native documents are backed up daily to Si. Immich evaluation is pending.</desc>'
                 '<g font-family="DejaVu Sans, sans-serif">')
    rect(0, 0, 1800, 2140, "#F3F6F9", "none", 0)
    text(48, 64, "The fleet. The files. The recovery paths.", 39, INK, 700)
    text(48, 103, "Current backup configuration • locations and relationships • schedules in HKT", 20, MUTED)
    rect(48, 126, 1704, 62, "#EAF6F0", "#BADCCC", 12)
    text(70, 153, "CLOUDFLARE  /  WEEKLY RESTIC BACKUP TO FI SECONDARY DISK", 17, GREEN, 700)
    text(70, 176, "DNS + KV exports and R2 objects · Sunday 03:00 HKT · 1 weekly + 1 monthly snapshot", 17, GREEN)

    text(48, 233, "01  LOCATIONS", 17, BLUE, 700)
    text(1752, 233, "Grouped cards indicate ownership / containment, not a copy", 17, MUTED, anchor="end")
    for x in (40, 620, 1200):
        rect(x, 253, 560, 292)
    place(64, 274, "desktop", "fi", "Desktop", "Main disk: work + independent Si app copy")
    place(93, 353, "disk", "fiX", "Secondary desktop SSD", "Cloudflare Restic destination", GREEN)
    PARTS.append('<path d="M80 324v46h8" fill="none" stroke="#A9BAC9" stroke-width="2"/>')
    place(64, 450, "laptop", "li", "Laptop", "Local work + fallback private-file backup")
    place(644, 274, "server", "si", "Server", "Applications + local recovery repository")
    place(673, 353, "pool", "siS", "Storage pool", "5 data disks • mergerfs")
    place(673, 450, "shield", "siP", "Parity", "2 parity disks • SnapRAID", PURPLE)
    PARTS.append('<path d="M660 324v145h8M660 371h8" fill="none" stroke="#A9BAC9" stroke-width="2"/>')
    place(1224, 274, "cloud", "gi", "Google", "Provider grouping • not a backup destination")
    place(1253, 353, "drive", "giD", "Google Drive", "Shared files + cloud-only archives / docs")
    place(1253, 450, "photo", "giP", "Google Photos", "TODO: evaluate Immich on Si", AMBER)
    PARTS.append('<path d="M1240 324v145h8M1240 371h8" fill="none" stroke="#A9BAC9" stroke-width="2"/>')
    rect(40, 561, 1720, 86, "#EAF0F6", "none")
    node(64, 577, "cloud", "cf / cfR2  Cloudflare", "DNS + KV + R2 archives / assets", TEAL)
    node(644, 577, "git", "git  Git remotes", "Committed code + config history", TEAL)
    node(1224, 577, "key", "bw  Bitwarden", "Vault / selected credential provisioning", TEAL)

    text(48, 689, "02  IMPLEMENTED ROUTES", 17, BLUE, 700)
    text(1752, 689, "Each lane is a separate scope • repeated device IDs are intentional", 17, MUTED, anchor="end")
    lane(711, "A", "Personal artefacts", "Local documents / media / projects / resources")
    node(72, 764, "desktop", "fi + li", "Local working folders")
    arrow(315, 505, 789, "rclone bisync", BLUE, both=True)
    node(525, 764, "drive", "giD", "Shared private folders")
    node(945, 764, "desktop", "fi / li", "Fi daily; Li fallback")
    arrow(1190, 1380, 789, "Restic snapshot")
    node(1400, 764, "pool", "siS", "Client repos • daily to annual bands", GREEN)

    lane(855, "B", "Applications + library", "SQLite / DB exports + app state + configs + public/library")
    node(72, 908, "server", "si", "Live apps + library")
    arrow(353, 613, 933, "export + snapshot")
    node(637, 908, "disk", "si · disk42 recovery", "Daily • 7D / 4W • outside parity", GREEN)
    arrow(1025, 1310, 933, "Restic copy")
    node(1330, 908, "desktop", "fi · main disk", "Weekly + daily catch-up", GREEN)

    lane(999, "C", "Device archives + cloud recovery", "Selected config / state / secrets; R2 also holds public assets")
    node(72, 1052, "archive", "fi + li + si", "Selected device folders")
    arrow(353, 613, 1077, "age archive + upload")
    node(637, 1052, "cloud", "cfR2 + DNS / KV", "Daily archives • per-folder retention", TEAL)
    arrow(1040, 1310, 1077, "export + Restic", GREEN)
    node(1330, 1052, "disk", "fiX · secondary SSD", "Restore verified · weekly active", GREEN)

    lane(1143, "D", "Bulk storage resilience", "Configured parity scope only; no version history")
    node(72, 1196, "pool", "siS · data disks", "Bulk media + configured files")
    arrow(400, 710, 1221, "SnapRAID parity", PURPLE)
    node(735, 1196, "shield", "siP · parity disks", "Daily sync • weekly scrub", PURPLE)
    text(1210, 1215, "Excluded: meta / downloads /", 18, MUTED)
    text(1210, 1241, "recovery-preservation", 18, MUTED)

    lane(1287, "E", "Code, configs + credentials", "History → deployment; vault → runtime secrets")
    node(72, 1340, "code", "Local repos", "Committed changes")
    arrow(318, 510, 1365, "Git push / pull", BLUE, both=True)
    node(530, 1340, "git", "git", "Code + config source", TEAL)
    arrow(795, 1060, 1365, "Tjikup / Tjikup", TEAL)
    node(1080, 1340, "config", "fi / li / si", "Applied configuration", TEAL)
    arrow(1575, 1360, 1365, "provision", TEAL)
    node(1600, 1340, "key", "bw", "Secrets", TEAL)

    lane(1431, "F", "Cloud-only collections", "Drive archives and native docs are backed up to Si")
    node(72, 1484, "drive", "giD · archives + mail", "Daily encrypted Restic backup on Si")
    node(650, 1484, "document", "giD · native documents", "Export + daily backup • 1D / 1W / 1M", GREEN)
    node(1230, 1484, "photo", "giP · personal photos", "TODO: evaluate Immich on Si", AMBER)

    text(48, 1605, "03  CONTENT ICONS", 17, BLUE, 700)
    text(1752, 1605, "Content tags can overlap • archive = inactive material • backup = recovery copy", 17, MUTED, anchor="end")
    content = [
        ("archive", "Archives", "Themed, inactive collections"),
        ("backup", "Backups", "Phone / OS / DB snapshots"),
        ("code", "Code", "Git-backed repositories"),
        ("folder", "Personal artefacts", "Docs / media / projects / resources"),
        ("download", "Downloads", "Staging; not backed up"),
        ("media", "Media", "Movies / shows / books / audio"),
        ("photo", "Photos", "Personal images"),
        ("assets", "Assets", "Public images / dataset releases"),
        ("config", "Configs", "Dotfiles / scripts / templates"),
        ("key", "Secrets", "Keys / credentials / recovery"),
        ("mail", "Mail", "Messages / attachments / indexes"),
        ("pool", "App state + databases", "Mutable data / native exports"),
        ("document", "Cloud-native docs", "Google Docs / Sheets / Slides / Drawings"),
        ("assets", "Recovery software", "Ephemera 2.0.0 → giD backups / software"),
        ("download", "Disposable data", "Caches / builds / temp files"),
    ]
    for i, (kind, title, subtitle) in enumerate(content):
        x = 40 + (i % 3) * 580
        y = 1626 + (i // 3) * 84
        rect(x, y, 560, 72)
        icon(kind, x + 16, y + 18, MUTED)
        text(x + 62, y + 29, title, 19, INK, 650)
        text(x + 62, y + 54, subtitle, 16, MUTED)
    text(48, 2072, "BLUE  sync / Git       GREEN  versioned recovery       PURPLE  parity       TEAL  hosting / deployment       AMBER  pending / unconfirmed", 17, MUTED)
    text(48, 2103, "Coverage limits: client repos have no Fi copy; Google Photos has no independent copy. Ephemera’s final image is preserved on Drive.", 17, MUTED)
    PARTS.append("</g></svg>")
    OUT.write_text("\n".join(PARTS) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png", action="store_true", help="Also render a PNG with CairoSVG")
    args = parser.parse_args()
    render()
    if args.png:
        import cairosvg

        cairosvg.svg2png(url=str(OUT), write_to=str(OUT.with_suffix(".png")))


if __name__ == "__main__":
    main()
