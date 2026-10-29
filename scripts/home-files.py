#!/usr/bin/env python3
"""Apply the explicit home manifest, preserving GTK's runtime theme selection."""
import json
import argparse
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from device_policy import context, profile


def runtime_context(repo):
    live = {}
    for version in (3, 4):
        path = Path.home() / f'.config/gtk-{version}.0/settings.ini'
        lines = path.read_text().splitlines() if path.is_file() else []
        live[f'gtk{version}_icon_theme'] = next((line.split('=', 1)[1] for line in lines
                                               if line.startswith('gtk-icon-theme-name=')), '')
    return {**context(repo), 'live': live}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'plan', 'apply'], nargs='?', default='plan')
    parser.add_argument('--group')
    options = parser.parse_args()
    action = options.action
    repo = Path(__file__).resolve().parents[1]
    host = socket.gethostname()
    manifest = repo / 'native/home' / f'files-{host}.json'
    portable = not manifest.is_file()
    if portable and profile():
        manifest = repo / 'native/home/files-device.json'
    if not manifest.is_file():
        raise SystemExit(f'No home file policy for {host}')
    if options.group:
        known = json.loads((repo / 'native/home/groups.json').read_text())
        if options.group not in known:
            parser.error('Unknown home file group: ' + options.group)
        entries = json.loads((repo / 'native/home' / ('portable-files.json' if portable else 'files.json')).read_text())
        if not any(entry.get('group') == options.group for entry in entries):
            print('SKIP    - ' + options.group + ' configuration  not enrolled on this device')
            return 0
    needs_unit_migration = False
    # Standalone dotjik apply must honor the same safe unit migration as the workflow.
    if action == 'apply' and options.group in (None, 'base'):
        needs_unit_migration = bool(runpy.run_path(str(repo / 'scripts/migrate-sync-units.py'))['legacy_units']())
        migration = subprocess.run([sys.executable, str(repo / 'scripts/migrate-sync-units.py')],
                                   capture_output=True, text=True)
        if migration.returncode:
            print('Synctjik schedule migration is not ready; leave running jobs alone and retry after they finish.',
                  file=sys.stderr)
            return 2
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'tjikup/files/home'
    binary = os.environ.get('TJIKUP_BINARY', str(Path.home() / '.local/bin/tjikup'))
    identifier = json.loads(manifest.read_text())['id']
    with tempfile.TemporaryDirectory(prefix='tjikup-home-context-') as temporary:
        context = Path(temporary) / 'context.json'
        context.write_text(json.dumps(runtime_context(repo)))
        args = [binary, 'files', action, '--manifest', str(manifest), '--context-file', str(context),
                '--state-dir', str(state)]
        if options.group:
            args += ['--group', options.group]
        if not portable and not (state / (identifier + '.json')).exists():
            if action == 'check':
                return 1  # Apply also records identical files as the first baseline.
        if not portable and action == 'apply':
            try:
                runpy.run_path(str(repo / 'scripts/migrate-home-files.py'))['adopt'](repo, manifest, state, args)
            except RuntimeError as error:
                print(error, file=sys.stderr)
                return 2
        result = subprocess.call(args)
        if result == 0 and needs_unit_migration:
            # Do not disable existing schedules if rendering/adoption/file apply failed.
            return subprocess.call([sys.executable, str(repo / 'scripts/migrate-sync-units.py'), '--retire'])
        return result


if __name__ == '__main__':
    raise SystemExit(main())
