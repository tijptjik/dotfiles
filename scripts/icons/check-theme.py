#!/usr/bin/env python3
"""Report icon overrides and missing fallbacks without changing the desktop."""
import argparse
import configparser
import json
import os
from pathlib import Path
from audit import inventory
from install import main_icon


def lookup(name, theme, roots, visited=None):
    visited = set() if visited is None else visited
    if theme in visited:
        return None
    visited.add(theme)
    inherited = []
    for root in roots:
        directory = root / theme
        for suffix in ('svg', 'png', 'xpm'):
            for path in directory.glob(f'**/{name}.{suffix}'):
                if path.is_file():
                    return path
        metadata = directory / 'index.theme'
        if metadata.is_file():
            config = configparser.ConfigParser(interpolation=None, strict=False)
            config.read(metadata)
            inherited.extend(config.get('Icon Theme', 'Inherits', fallback='').split(','))
    for parent in [*inherited, 'hicolor']:
        if parent and (found := lookup(name, parent.strip(), roots, visited)):
            return found
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', default='rose-punk-illustrated')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    system = [Path(p) for p in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]
    roots = [data / 'applications', home / '.local/share/flatpak/exports/share/applications',
             *[p / 'applications' for p in system], Path('/var/lib/flatpak/exports/share/applications')]
    icons = [data / 'icons', home / '.icons', *[p / 'icons' for p in system]]
    def available(name):
        return lookup(name, args.theme, icons) or any(
            (root / 'pixmaps' / f'{name}.{suffix}').is_file()
            for root in [data, *system] for suffix in ('svg', 'png', 'xpm'))

    issues = []
    for desktop in inventory(roots):
        path = next(root / desktop for root in roots if (root / desktop).is_file())
        name = main_icon(path.read_text())
        kind = ('absolute icon path' if name.startswith('/') else
                'theme-specific icon name' if name.startswith('rose-punk-') else
                'missing icon' if not name or not available(name) else None)
        if kind:
            issues.append({'desktop': desktop, 'issue': kind, 'icon': name})
    for path in (data / 'icons/hicolor').rglob('*'):
        if path.is_symlink() and any(path.resolve().is_relative_to((data / 'icons' / name).resolve())
                                    for name in ('rose-punk', 'rose-punk-illustrated')):
            issues.append({'path': str(path), 'issue': 'theme artwork in hicolor'})
    if args.json:
        print(json.dumps(issues, indent=2))
    else:
        print(f'{len(issues)} icon switching/lookup issues for {args.theme}')
        for issue in issues:
            print(f'{issue["issue"]}: {issue.get("desktop", issue.get("path"))} {issue.get("icon", "")}')
    return bool(issues)


if __name__ == '__main__':
    raise SystemExit(main())
