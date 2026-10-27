#!/usr/bin/env python3
"""Report app-icon coverage using Hamr's desktop-entry inclusion rules."""
import configparser
import fnmatch
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def inventory(roots=None):
    if roots is None:
        roots=[Path.home()/'.local/share/applications', Path.home()/'.local/share/flatpak/exports/share/applications',
           Path('/usr/share/applications'),Path('/usr/local/share/applications'),
           Path('/var/lib/flatpak/exports/share/applications'),Path('/var/lib/snapd/desktop/applications')]
    rows={}
    seen=set()
    for root in roots:
        for path in sorted(root.glob('*.desktop')):
            # A hidden user override must also suppress the system launcher.
            if path.name in seen:
                continue
            seen.add(path.name)
            config=configparser.ConfigParser(interpolation=None,strict=False)
            try:
                config.read(path)
                entry=config['Desktop Entry']
            except (configparser.Error,KeyError,UnicodeError):
                continue
            if entry.get('Type')!='Application' or not entry.get('Name'):
                continue
            if any(entry.get(k,'').lower()=='true' for k in ('Hidden','NoDisplay')):
                continue
            rows[path.name]=entry['Name']
    return rows


def main():
    mapping=json.loads((HERE/'apps.json').read_text())
    rows=inventory();missing=[];families=set()
    for desktop,name in rows.items():
        key=next((k for k,patterns in mapping.items() if any(fnmatch.fnmatchcase(desktop,p) for p in patterns)),None)
        if key:families.add(key)
        else:missing.append((desktop,name))
    print(f'{len(rows)-len(missing)}/{len(rows)} desktop IDs covered across {len(families)} installed app families')
    for desktop,name in missing:print(f'MISSING: {desktop} ({name})')
    return bool(missing)


if __name__=='__main__':sys.exit(main())
