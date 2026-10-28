#!/usr/bin/env python3
"""Create declared home Git checkouts without overwriting or resetting local work."""
import json
from pathlib import Path
import socket
import subprocess
import sys


def main():
    if sys.argv[1:] not in [['check'], ['apply']]:
        raise SystemExit('usage: home-repositories.py check|apply')
    repo = Path(__file__).resolve().parents[1]
    missing = []
    for entry in json.loads((repo / 'native/home/repositories.json').read_text()):
        if socket.gethostname() not in entry['hosts']:
            continue
        target = Path.home() / entry['path']
        if target.exists():
            result = subprocess.run(['git', '-C', str(target), 'rev-parse', '--show-toplevel'],
                                    capture_output=True, text=True)
            if result.returncode or Path(result.stdout.strip()) != target.resolve():
                raise SystemExit(f'Existing path is not the expected Git checkout: {target}')
        else:
            missing.append((target, entry['url']))
    if sys.argv[1] == 'check':
        return int(bool(missing))
    for target, url in missing:
        subprocess.run(['git', 'clone', '--', url, str(target)], check=True)
    print(f'{"APPLY" if missing else "SKIP"}: {len(missing)} home repositories created')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
