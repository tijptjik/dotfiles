#!/usr/bin/env python3
"""Cache only builds/installs; require matching source AND deployed output bytes."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

IGNORED = {'.git', 'dist', 'target', '__pycache__', '.venv', 'node_modules'}


def fingerprint(paths, *, source=False):
    digest = hashlib.sha256()
    def visit(path):
        digest.update(str(path).encode())
        info = path.lstat()
        digest.update(str(stat.S_IMODE(info.st_mode)).encode())
        if path.is_symlink():
            digest.update(b'link' + os.readlink(path).encode())
            # Verify the referent as well: dangling/replaced links are not current.
            if not source:
                digest.update(path.read_bytes())
        elif path.is_dir():
            for child in sorted(path.iterdir()):
                if child.name == '__pycache__' or child.suffix in {'.pyc', '.pyo'}:
                    continue
                if not source or child.name not in IGNORED:
                    visit(child)
        else:
            digest.update(path.read_bytes())
    try:
        for path in paths:
            visit(Path(path))
    except (OSError, ValueError):
        return None
    return digest.hexdigest()


def cached_install(name, inputs, outputs, command):
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'tjikup/install'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / f'{name}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = state / f'{name}.json'
        before = fingerprint(inputs, source=True)
        deployed = fingerprint(outputs)
        installed = any(os.path.lexists(path) for path in outputs)

        def report(verb, note):
            print(f'{verb:<7} ✓ {name}    {note}')
            print(f'__stage_verb__:{verb}')
            print(f'__stage_note__:{note}')

        try:
            saved = json.loads(record.read_text())
        except (OSError, ValueError):
            saved = {}
        if before and deployed and saved == {'inputs': before, 'outputs': deployed}:
            report('SKIP', 'no changes')
            return 0
        result = subprocess.run(command, check=False)
        if result.returncode:
            return result.returncode
        after = fingerprint(outputs)
        # Missing outputs or concurrent source changes cannot create a valid stamp.
        if before and after and before == fingerprint(inputs, source=True):
            fd, staged = tempfile.mkstemp(dir=state, prefix=f'.{name}.')
            try:
                with os.fdopen(fd, 'w') as stream:
                    json.dump({'inputs': before, 'outputs': after}, stream)
                os.replace(staged, record)
            finally:
                Path(staged).unlink(missing_ok=True)
        if deployed and after == deployed:
            report('SKIP', 'no changes')
        elif installed:
            report('UPDATE', 'updated' if deployed else 'repaired')
        else:
            report('INSTALL', 'installed')
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', choices=['tjikup', 'notjik', 'bartjik', 'greetjik', 'runtjik'])
    parser.add_argument('--input', action='append', required=True)
    parser.add_argument('--output', action='append', required=True)
    separator = sys.argv.index('--') if '--' in sys.argv else len(sys.argv)
    args = parser.parse_args(sys.argv[1:separator])
    command = sys.argv[separator + 1:]
    if not command:
        parser.error('missing install command')
    return cached_install(args.name, args.input, args.output, command)


if __name__ == '__main__':
    raise SystemExit(main())
