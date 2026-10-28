#!/usr/bin/env python3
"""Temporary Chezmoi adapter for unported system templates; no Chezetc dependency."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from device_policy import context


def main():
    repo = Path(__file__).resolve().parents[1]
    home = Path.home()
    host = socket.gethostname()
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'tjikup/legacy-system'
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = state / 'config.toml'
    values = {'sourceDir': str(repo / 'system/etc'), 'destDir': '/etc', 'encryption': 'age'}
    text = ''.join(f'{key} = {json.dumps(value)}\n' for key, value in values.items())
    text += '\n[age]\nidentity = ' + json.dumps(str(home / '.keys/chezmoi.txt')) + '\n'
    text += '\n[data]\nhostname = ' + json.dumps(host) + '\n'
    policy = context(repo)
    for name, value in {'isClient': policy['is_client'], 'isDesktop': policy['is_desktop'], 'isLaptop': policy['is_laptop'], 'isServer': policy['is_server']}.items():
        text += f'{name} = {str(value).lower()}\n'
    if not config.exists() or config.read_text() != text:
        fd, name = tempfile.mkstemp(dir=state)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(text)
            os.replace(name, config)
        finally:
            Path(name).unlink(missing_ok=True)
    allowed = 'PATH,TJIKUP_COLOR,TJIKUP_NO_SPIN,TJIKUP_REPORT_FILE,TJIKUP_SKIP_PREFLIGHT,TJIKUP_COLUMNS,FLEET_DEFER_SYSTEM_HOOKS,TJIKUP_NO_SECTIONS,TJIKUP_STATUS_LINES'
    command = ['sudo', '-n', '--preserve-env=' + allowed, '--', 'chezmoi',
               '--config', str(config), '--persistent-state', str(state / 'chezmoistate.boltdb'),
               '--cache', str(state / 'cache'), *sys.argv[1:]]
    return subprocess.call(command)


if __name__ == '__main__':
    raise SystemExit(main())
