#!/usr/bin/env python3
"""Bake 32px Rose Punk sprites; runtime only needs the Python standard library.

Requires ImageMagick and Pillow on the build host.
Every fleet label has a catalog SVG. Missing mappings fail the build rather
than depending on whichever fallback font is installed. No runtime conversion.
"""
import base64
import io
import json
from pathlib import Path
import runpy
import subprocess
import zlib

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / 'native/home/files/.local/share/icons/rose-punk/scalable/apps'
CATALOG = runpy.run_path(str(ROOT / 'scripts/icons/icon_catalog.py'))
SOURCES = {
    'Zoom Workplace': 'zoom', 'ChatGPT Desktop': 'chatgpt',
    'Collie': 'collie', 'Docker': 'docker', 'Flatpak': 'flatpak', 'Herdr': 'herdr',
    'llmtrim': 'llmtrim', 'Nginx': 'nginx', 'Notifications': 'notjik', 'Greetjik': 'greetjik',
    'Power': 'power', 'Prowlarr': 'prowlarr', 'Python': 'python', 'Rust': 'rust',
    'Tailscale': 'tailscale', 'Tjikup': 'tjikup', 'Vite': 'vite',
    'Bartjik': 'bartjik', 'Notjik': 'notjik', 'Runtjik': 'runtjik',
    'Applications': 'software', 'Assets': 'file-roller', 'Assets (fonts)': 'fonts',
    'Assets (icon cache)': 'runtjik-grid', 'Assets (Rose Punk icons)': 'runtjik-grid',
    'Assets (symbolic link icon)': 'runtjik-grid',
    'Chezetc': 'chezetc', 'Chezmoi': 'chezmoi', 'Codex Desktop': 'codex',
    'Codex LB': 'codex-lb', 'Fedora': 'fedora-media-writer', 'Hyprvoice': 'hyprvoice',
    'Launcher': 'software', 'Media': 'video-player', 'Mullvad': 'mullvad',
    'NSS': 'passwords-and-keys', 'oo7': 'oo7', 'Storage': 'disks',
    'SnapRAID': 'snapraid', 'Strata': 'strata', 'Systemd': 'system-monitor',
    'Telegram': 'telegram', 'Terminal': 'terminal', 'Tippecanoe': 'tippecanoe',
    'Transmission': 'transmission', 'Zed': 'zed', '*': 'settings',
    'Google Chrome stable': 'chrome', 'Sublime Text': 'sublime-text', 'Obsidian': 'obsidian',
    'GDM': 'gnome',
    'Gitfetch': 'gitfetch',
    'Bitwarden': 'bitwarden', 'Fish': 'fish', 'UV': 'uv', 'FNM': 'fnm', 'Gum': 'gum',
    'Bun': 'bun', 'Solaar': 'solaar', 'Fcitx': 'fcitx-5-configuration', 'Codex': 'codex',
    'Zapzap': 'zapzap', 'Gtk-bookmarks': 'bookmarks', 'Local Changes': 'gitfetch',
    'Templates': 'gitfetch', 'Home and system': 'settings',
    'Dotjik': 'chezmoi', 'Systjik': 'chezetc', 'tjikOS': 'tjikup',
    'dotjik': 'chezmoi', 'systjik': 'chezetc', 'tjikos': 'tjikup',
    'Assets (user fonts)': 'fonts', 'Assets (font folder migration)': 'fonts',
}


def render(icons=None, services=None):
    glyphs = {**CATALOG['SERVICE_ICONS'], '*': '\uf013',
              **{f'Assets ({key})': value for key, value in CATALOG['ASSET_ICONS'].items()}}
    docker = CATALOG['DOCKER_SERVICES']
    sources = {**SOURCES, 'Plex': 'plex', 'Docker images': 'docker',
               **{name: entry['icon'] for name, entry in docker.items()}}
    missing = set(glyphs) - set(sources)
    if missing:
        raise ValueError(f'Fleet labels need explicit SVG mappings: {sorted(missing)}')
    sprites = {}
    for name in sorted(glyphs):
        key = sources[name]
        if name in docker or name == 'Plex':
            folder = ROOT / 'native/home/files/dockers/homepage/images/rose-punk'
            source = (folder / f'{key}.svg').read_bytes() if services is None else services[f'{key}.svg']
        else:
            source = (THEME / f'{key}.svg').read_bytes() if icons is None else icons[f'{key}.svg']
        png = subprocess.check_output(['magick', '-background', 'none', 'svg:-',
                                      '-resize', '32x32!', 'PNG32:-'], input=source)
        image = Image.open(io.BytesIO(png)).convert('RGBA')
        sprites[name] = base64.b64encode(zlib.compress(image.tobytes(), 9)).decode()
    return (json.dumps({'size': 32, 'format': 'zlib-base64-rgba', 'sprites': sprites}, indent=2) + '\n').encode()


def main():
    from icon_data import write_file
    target = ROOT / 'scripts/icons/icons32.json'
    data = render()
    write_file(target, data)
    print(f"Wrote {len(json.loads(data)['sprites'])} sprites to {target.relative_to(ROOT)}")


if __name__ == '__main__':
    main()
