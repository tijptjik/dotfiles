#!/usr/bin/env python3
"""Apply the explicit home manifest, preserving GTK's runtime theme selection."""
import json
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
    action = sys.argv[1] if len(sys.argv) == 2 else 'plan'
    if action not in {'check', 'plan', 'apply'}:
        raise SystemExit('usage: home-files.py check|plan|apply')
    repo = Path(__file__).resolve().parents[1]
    host = socket.gethostname()
    manifest = repo / 'native/home' / f'files-{host}.json'
    portable = not manifest.is_file()
    if portable and profile():
        manifest = repo / 'native/home/files-device.json'
    if not manifest.is_file():
        raise SystemExit(f'No home file policy for {host}')
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'tjikup/files/home'
    binary = os.environ.get('TJIKUP_BINARY', str(Path.home() / '.local/bin/tjikup'))
    identifier = json.loads(manifest.read_text())['id']
    with tempfile.TemporaryDirectory(prefix='tjikup-home-context-') as temporary:
        context = Path(temporary) / 'context.json'
        context.write_text(json.dumps(runtime_context(repo)))
        args = [binary, 'files', action, '--manifest', str(manifest), '--context-file', str(context),
                '--state-dir', str(state)]
        if not portable and not (state / (identifier + '.json')).exists():
            if action == 'check':
                return 1  # Apply also records identical files as the first baseline.
            if action == 'apply':
                try:
                    runpy.run_path(str(repo / 'scripts/migrate-home-files.py'))['adopt'](repo, manifest, state, args)
                except RuntimeError as error:
                    print(error, file=sys.stderr)
                    return 2
        return subprocess.call(args)


if __name__ == '__main__':
    raise SystemExit(main())
