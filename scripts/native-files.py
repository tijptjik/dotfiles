#!/usr/bin/env python3
"""Select this host's native file policy, keeping privilege boundaries explicit."""
import argparse
import json
import runpy
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from device_policy import context, profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scope', choices=['home', 'home-files', 'credentials', 'system'])
    parser.add_argument('action', choices=['check', 'plan', 'diff', 'apply'], nargs='?', default='plan')
    parser.add_argument('--group')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    host = socket.gethostname()
    binary = os.environ.get('TJIKUP_BINARY', str(Path.home() / '.local/bin/tjikup'))
    action = 'plan' if args.action == 'diff' else args.action
    if args.scope in {'home', 'home-files'}:
        status = subprocess.call([sys.executable, str(repo / 'scripts/home-files.py'), action,
                                  *(['--group', args.group] if args.group else [])])
        if args.scope == 'home-files' or status not in (0, 1) or action == 'apply' and status != 0:
            return status
        credentials = subprocess.call([sys.executable, __file__, 'credentials', args.action])
        return max(status, credentials)
    if args.scope == 'credentials':
        manifest = repo / 'native/home' / (host + '.json')
        if not manifest.is_file() and profile():
            manifest = repo / 'native/home/device.json'
        state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'tjikup/files/home'
        prefix = []
    else:
        return subprocess.call([sys.executable, str(repo / 'scripts/system-files.py'), action])
    if not manifest.is_file():
        parser.error(f'No native manifest for host {host}')
    if args.scope == 'credentials' and host in {'fi', 'li', 'si'}:
        identifier = json.loads(manifest.read_text())['id']
        if not (state / (identifier + '.json')).exists():
            if action == 'check':
                return 1
            if action == 'apply':
                try:
                    runpy.run_path(str(repo / 'scripts/migrate-native-home.py'))['adopt'](repo, manifest, state, binary)
                except RuntimeError as error:
                    print(error, file=sys.stderr)
                    return 2
    with tempfile.TemporaryDirectory(prefix='tjikup-device-context-') as directory:
        context_path = Path(directory) / 'context.json'
        context_path.write_text(json.dumps(context(repo)))
        return subprocess.call([*prefix, binary, 'files', action, '--manifest', str(manifest),
                                '--state-dir', str(state), *(['--context-file', str(context_path)] if args.scope == 'credentials' else [])])


if __name__ == '__main__':
    raise SystemExit(main())
