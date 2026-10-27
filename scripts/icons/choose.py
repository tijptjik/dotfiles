#!/usr/bin/env python3
"""Select an installed icon theme without pinning it in managed configuration."""
import argparse
import configparser
import os
from pathlib import Path

from install import select_theme

THEME = 'rose-punk-illustrated'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('theme', nargs='?', default=THEME, help='installed theme ID (default: Rose Punk)')
    args = parser.parse_args()
    theme = THEME if args.theme == 'Rose Punk' else args.theme
    if theme in ('.', '..') or '/' in theme:
        parser.error('expected an installed theme name, not a path')
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    roots = [data / 'icons', home / '.icons']
    roots += [Path(p) / 'icons' for p in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]
    metadata = next((root / theme / 'index.theme' for root in roots if (root / theme / 'index.theme').is_file()), None)
    if metadata is None:
        parser.error(f'icon theme is not installed: {theme}')
    config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
    select_theme(config, theme, bool(os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY')))
    details = configparser.ConfigParser(interpolation=None)
    details.read(metadata)
    print('Selected ' + details.get('Icon Theme', 'Name', fallback=theme))


if __name__ == '__main__':
    main()
