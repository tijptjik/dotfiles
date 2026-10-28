#!/usr/bin/env python3
"""Adopt existing credentials only when they match their previous Chezmoi template."""
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile


def adopt(repo, manifest, state, binary):
    spec = json.loads(manifest.read_text())
    if (state / (spec['id'] + '.json')).exists():
        return
    sources = json.loads((repo / 'native/home/migration-sources.json').read_text())
    user_home = spec['context']['user']['home']
    token = Path(user_home) / '.config/bws/environment'
    if token.exists() or token.is_symlink():
        info = token.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError('Bitwarden token must be a regular file owned by this user')
        token.chmod(0o600)
    with tempfile.TemporaryDirectory(prefix='tjikup-adopt-') as directory:
        temporary = Path(directory)
        baseline = {'version': 1, 'id': spec['id'], 'host': spec['host'], 'entries': []}
        for index, entry in enumerate(spec['entries']):
            target = Path(entry['path'].replace('{{ user.home }}', user_home))
            if target.is_symlink():
                raise RuntimeError(f'Refusing credential symlink: {target}')
            if not target.exists():
                baseline['entries'].append({'kind': 'absent', 'path': str(target)})
                continue
            info = target.stat()
            if not target.is_file() or info.st_uid != os.getuid():
                raise RuntimeError(f'Expected a regular credential owned by this user: {target}')
            current = target.read_bytes()
            if not entry.get('create_only'):
                relative = str(target.relative_to(user_home))
                source = next(name for name, dest in sources.items() if dest == relative)
                rendered = subprocess.run([
                    'chezmoi', '--source', str(repo / 'home'), 'execute-template',
                    '--file', str(repo / 'home' / source),
                ], capture_output=True)
                if rendered.returncode or rendered.stdout != current:
                    raise RuntimeError(f'Cannot adopt {target}: live file differs from its legacy template; reconcile it first')
            # Private temporary sources; adopt actual metadata without target writes.
            source = temporary / str(index)
            source.write_bytes(current)
            source.chmod(0o600)
            baseline['entries'].append({'kind': 'file', 'path': str(target), 'source': source.name,
                                        'mode': format(info.st_mode & 0o777, '04o'),
                                        'uid': info.st_uid, 'gid': info.st_gid})
        filename = temporary / 'manifest.json'
        filename.write_text(json.dumps(baseline))
        result = subprocess.run([binary, 'files', 'apply', '--manifest', str(filename),
                                 '--state-dir', str(state)], capture_output=True, text=True)
        if result.returncode or 'SKIP: 0 changed,' not in result.stdout:
            raise RuntimeError('Credential adoption failed; no legacy ownership should be removed')
        print('Adopted existing credentials without changing targets.')
