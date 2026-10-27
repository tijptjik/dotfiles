#!/usr/bin/env python3
"""Apply only icon overrides to installed desktop entries; retain original launch commands."""
import argparse
import fnmatch
import json
import os
from pathlib import Path
import re
import subprocess


def with_icon(text, icon):
    """Replace the main entry icon; preserve actions, comments and localized fields."""
    lines = text.splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        if line.strip().startswith('['):
            if inside:
                lines.insert(i, f'Icon={icon}\n')
                return ''.join(lines)
            inside = line.strip() == '[Desktop Entry]'
        elif inside and line.startswith('Icon='):
            lines[i] = f'Icon={icon}\n'
            return ''.join(lines)
    if inside:
        return ''.join(lines).rstrip('\n') + f'\nIcon={icon}\n'
    raise ValueError('Missing Desktop Entry section')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true', help='restore entries unchanged since this installation')
    args = parser.parse_args()
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'rose-punk-icons'
    state.mkdir(parents=True, exist_ok=True)
    record_path = state / 'desktop-overrides.json'
    records = json.loads(record_path.read_text()) if record_path.exists() else {}
    if args.restore:
        for name, record in list(records.items()):
            target = data / 'applications' / name
            if target.exists() and target.read_text() == record['installed']:
                if record['original'] is None:
                    target.unlink()
                else:
                    target.write_text(record['original'])
                del records[name]
        record_path.write_text(json.dumps(records, indent=2) + '\n')
        return
    mapping = json.loads(Path(__file__).with_name('apps.json').read_text())
    roots = [data / 'applications', home / '.local/share/flatpak/exports/share/applications',
             Path('/usr/local/share/applications'), Path('/usr/share/applications'),
             Path('/var/lib/flatpak/exports/share/applications')]
    seen = set()
    count = 0
    for root in roots:
        for source in sorted(root.glob('*.desktop')):
            if source.name in seen:
                continue
            seen.add(source.name)
            key = next((key for key, patterns in mapping.items()
                        if any(fnmatch.fnmatchcase(source.name, p) for p in patterns)), None)
            if not key:
                continue
            if not (data / f'icons/rose-punk/scalable/apps/{key}.svg').is_file():
                raise RuntimeError(f'Missing deployed icon: {key}')
            target = data / 'applications' / source.name
            text = source.read_text()
            updated = with_icon(text, 'rose-punk-' + key)
            if text == updated:
                continue
            # Save the latest original when an external app rewrites its desktop entry.
            if source.name not in records or text != records[source.name]['installed']:
                records[source.name] = {'original': text if source == target else None}
            records[source.name]['installed'] = updated
            # Persist recovery data before changing the desktop entry.
            record_path.write_text(json.dumps(records, indent=2) + '\n')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(updated)
            count += 1
    print(f'Rose Punk icons: updated {count} desktop entries')
    for theme in ('rose-punk', 'rose-punk-illustrated'):
        if (data / 'icons' / theme / 'index.theme').exists():
            subprocess.run(['gtk-update-icon-cache', '--force', str(data / 'icons' / theme)], check=True)
    subprocess.run(['gtk-update-icon-cache', '--force', '--ignore-theme-index', str(data / 'icons/hicolor')], check=True)
    subprocess.run(['update-desktop-database', str(data / 'applications')], check=True)


if __name__ == '__main__':
    main()
