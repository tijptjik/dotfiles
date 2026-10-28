#!/usr/bin/env python3
"""Retire proven duplicate desktop producers, archiving every changed live file."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

TELEGRAM = 'org.telegram.desktop._3e485da34fc040f9218e3891ecde1e6c.desktop'
REPLACEMENTS = {
    'dev.zed.desktop': 'dev.zed.Zed.desktop',
    'zed.desktop': 'dev.zed.Zed.desktop',
    'com.brave.Browser.desktop': 'brave-browser.desktop',
    'com.google.Chrome.canary.desktop': 'google-chrome-canary.desktop',
    'org.telegram.desktop': TELEGRAM,
    'FFPWA-01KC3V7SZSJ8PMK49J7QBTP2FK.desktop': 'FFPWA-01KCGW1793YX2BA145Z4NWQ2XY.desktop',
    'FFPWA-01KVFQER39ASXCZ26D7724G54G.desktop': 'FFPWA-01KVFSZ3Z9JKBJMMTW9DENGR0N.desktop',
}


def cleanup(home, apply=False):
    applications = home / '.local/share/applications'
    registry = home / '.local/share/firefoxpwa/config.json'
    sites = json.loads(registry.read_text()).get('sites', {}) if registry.exists() else None
    archive = home / '.local/state/runtjik/desktop-entry-archives' / time.strftime('%Y%m%dT%H%M%S')
    changed = []
    def backup(path):
        target = archive / path.relative_to(home)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    for old, new in REPLACEMENTS.items():
        source, replacement = applications / old, applications / new
        if not source.is_file() or not replacement.is_file():
            continue
        if old.startswith('FFPWA-'):
            old_id, new_id = old[6:-8], new[6:-8]
            if sites is None or old_id in sites or new_id not in sites:
                continue  # Only remove a proven orphan; never delete a registered site.
        changed.append({'remove': old, 'keep': new})
        if apply:
            backup(source)
            if old == 'com.brave.Browser.desktop':
                # Preserve the explicit Wayland/colour options on the canonical RPM ID.
                backup(replacement)
                replacement.write_bytes(source.read_bytes())
            source.unlink()
    mime = home / '.config/mimeapps.list'
    mime_changed = False
    if mime.exists():
        text = mime.read_text()
        revised = text
        for item in changed:
            revised = revised.replace(item['remove'], item['keep'])
        revised = revised.replace('application/x-zerosize=evince.desktop', 'application/x-zerosize=org.gnome.Papers.desktop')
        mime_changed = revised != text
        if apply and mime_changed:
            backup(mime)
            mime.write_text(revised)
    if apply and shutil.which('update-desktop-database') and applications.exists():
        subprocess.run(['update-desktop-database', str(applications)], check=True)
    return {'changes': changed, 'mime_changed': mime_changed,
            'archive': str(archive) if apply and (changed or mime_changed) else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = cleanup(Path.home(), args.apply)
    if args.check:
        raise SystemExit(1 if result['changes'] or result['mime_changed'] else 0)
    print(json.dumps(result, indent=2))
