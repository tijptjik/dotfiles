"""Compare unowned live bytes with a private native staging render before adoption."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def adopt(manifest, state, apply_command):
    spec = json.loads(manifest.read_text())
    check = list(apply_command)
    check[2] = 'plan'
    result = subprocess.run([*check, '--json'], capture_output=True)
    try:
        rows = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise RuntimeError('Native adoption preflight failed; inspect the native plan') from None
    if result.returncode not in (0, 1, 2):
        raise RuntimeError('Native adoption preflight failed')
    state_file = state / (spec['id'] + '.json')
    owned = json.loads(state_file.read_text())['files'] if state_file.exists() else {}
    conflicts = [row for row in rows if row['action'] == 'conflict' and row['path'] not in owned]
    if not conflicts:
        return
    with tempfile.TemporaryDirectory(prefix='tjikup-native-adopt-') as directory:
        temporary = Path(directory)
        root = temporary / 'root'
        root.mkdir(mode=0o700)
        staged = list(apply_command)
        staged[staged.index('--state-dir') + 1] = str(temporary / 'state')
        result = subprocess.run([*staged, '--root', str(root)], capture_output=True)
        if result.returncode:
            raise RuntimeError('Native staging failed; no live file was adopted')
        baseline = {'version': 1, 'id': spec['id'], 'host': spec.get('host'), 'entries': []}
        for index, row in enumerate(conflicts):
            target = Path(row['path'])
            desired = root / str(target).lstrip('/')
            if target.is_symlink() or desired.is_symlink() or not target.is_file() or not desired.is_file():
                raise RuntimeError(f'Local changes require review before adopting {target}')
            info = target.stat()
            if info.st_uid != os.getuid() or target.read_bytes() != desired.read_bytes():
                raise RuntimeError(f'Local changes require review before adopting {target}')
            source = temporary / str(index)
            source.write_bytes(target.read_bytes())
            source.chmod(0o600)
            baseline['entries'].append({'kind': 'file', 'path': str(target), 'source': source.name,
                                       'mode': format(info.st_mode & 0o777, '04o'),
                                       'uid': info.st_uid, 'gid': info.st_gid})
        filename = temporary / 'baseline.json'
        filename.write_text(json.dumps(baseline))
        result = subprocess.run([apply_command[0], 'files', 'apply', '--manifest', str(filename),
                                 '--state-dir', str(state)], capture_output=True, text=True)
        if result.returncode or 'SKIP: 0 changed,' not in result.stdout:
            raise RuntimeError('Native adoption failed; no forced overwrite was attempted')
