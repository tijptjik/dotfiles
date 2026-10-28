#!/usr/bin/env python3
"""One-time bridge for metadata-only differences from the retired home renderer."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def adopt(repo, manifest, state, apply_command):
    check = [*apply_command]
    check[2] = 'plan'
    check.append('--json')
    result = subprocess.run(check, capture_output=True, text=True)
    if result.returncode not in (0, 1, 2) or not result.stdout:
        raise RuntimeError('Native home preflight failed; inspect the native plan before retrying')
    rows = json.loads(result.stdout)
    conflicts = [row for row in rows if row['action'] == 'conflict']
    if not conflicts:
        return
    spec = json.loads(manifest.read_text())
    user_home = Path(spec['context']['user']['home'])
    mapping = json.loads((repo / 'native/home/file-migration-sources.json').read_text())
    with tempfile.TemporaryDirectory(prefix='tjikup-home-adopt-') as directory:
        temporary = Path(directory)
        baseline = {'version': 1, 'id': spec['id'], 'host': spec['host'], 'entries': []}
        for index, row in enumerate(conflicts):
            target = Path(row['path'])
            relative = str(target.relative_to(user_home))
            source = repo / 'home' / mapping.get(relative, '.missing-migration-source')
            if target.is_symlink() or not target.is_file() or not source.is_file():
                raise RuntimeError(f'Local changes require review before adopting {target}')
            info = target.stat()
            if info.st_uid != os.getuid():
                raise RuntimeError(f'Cannot adopt a file owned by another user: {target}')
            if source.name.endswith('.tmpl'):
                old = subprocess.run(['chezmoi', '--source', str(repo / 'home'), 'execute-template',
                                      '--file', str(source)], capture_output=True)
                if old.returncode:
                    raise RuntimeError(f'Legacy comparison failed for {target}')
                expected = old.stdout
            else:
                expected = source.read_bytes()
            current = target.read_bytes()
            if current != expected:
                raise RuntimeError(f'Local changes require review before adopting {target}')
            file = temporary / str(index)
            file.write_bytes(current)
            file.chmod(0o600)
            baseline['entries'].append({'kind': 'file', 'path': str(target), 'source': file.name,
                                        'mode': format(info.st_mode & 0o777, '04o'),
                                        'uid': info.st_uid, 'gid': info.st_gid})
        filename = temporary / 'baseline.json'
        filename.write_text(json.dumps(baseline))
        result = subprocess.run([apply_command[0], 'files', 'apply', '--manifest', str(filename),
                                 '--state-dir', str(state)], capture_output=True, text=True)
        if result.returncode or 'SKIP: 0 changed,' not in result.stdout:
            raise RuntimeError('Native home adoption failed; no forced overwrite was attempted')
