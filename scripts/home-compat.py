#!/usr/bin/env python3
"""Home file commands backed by Tjikup's native policy."""
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys


def source_path(repo, target):
    base = repo / 'native/home'
    host = socket.gethostname()
    destination = str(Path(target).expanduser().absolute())
    for filename in [base / f'files-{host}.json', base / f'{host}.json']:
        spec = json.loads(filename.read_text())
        entries = list(spec.get('entries', []))
        for name in spec.get('entries_files', []):
            entries.extend(json.loads((base / name).read_text()))
        for entry in entries:
            condition = entry.get('when')
            if condition and condition.startswith('hostname in ') and host not in json.loads(condition[12:]):
                continue
            path = entry['path'].replace('{{ user.home }}', spec['context']['user']['home'])
            if path == destination:
                return base / entry['source'] if 'source' in entry else base / 'files.json'
    raise ValueError(f'No native source for {destination}; declare new targets in native/home/files.json')


def main():
    repo = Path(__file__).resolve().parents[1]
    args = sys.argv[1:] or ['plan']
    if args[0] in {'check', 'plan', 'diff', 'apply'} and len(args) == 1:
        return subprocess.call([sys.executable, str(repo / 'scripts/native-files.py'), 'home', *args])
    if args == ['source-path']:
        print(repo / 'native/home')
        return 0
    if args[0] in {'source-path', 'edit'} and len(args) == 2:
        try:
            source = source_path(repo, args[1])
        except ValueError as error:
            print(error, file=sys.stderr)
            return 2
        if args[0] == 'source-path':
            print(source)
            return 0
        editor = shlex.split(os.environ.get('VISUAL') or os.environ.get('EDITOR') or 'zed --wait')
        return subprocess.call([*editor, str(source)])
    print('Use dotjik check|plan|diff|apply, source-path [TARGET], or edit TARGET. Add new file entries in native/home/files.json.', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
