#!/usr/bin/env python3
"""Native system policy; age decrypts server inputs only into a private staging directory."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from device_policy import profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'check', 'apply', 'diff'])
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    host = socket.gethostname()
    base = repo / 'system/native' / host
    if host not in {'fi', 'li', 'si'}:
        if not profile():
            parser.error('Enroll this device first')
        print('SKIP: no machine-specific system files enrolled; recipes manage selected packages')
        return 0
    binary = os.environ.get('TJIKUP_BINARY', str(Path.home() / '.local/bin/tjikup'))
    action = 'plan' if args.action == 'diff' else args.action
    with tempfile.TemporaryDirectory(prefix='tjikup-system-') as directory:
        private = Path(directory)
        manifest = base / 'manifest.json'
        mapping = base / 'encrypted.json'
        encrypted = json.loads(mapping.read_text()) if mapping.exists() else {}
        if encrypted:
            shutil.copytree(base, private / 'policy')
            manifest = private / 'policy/manifest.json'
            identity = Path.home() / '.keys/chezmoi.txt'  # Existing age identity; no Chezmoi process.
            for name, source in encrypted.items():
                for relative in (name, source):
                    if Path(relative).is_absolute() or '..' in Path(relative).parts:
                        raise RuntimeError('Invalid encrypted policy path')
                try:
                    result = subprocess.run(['age', '--decrypt', '--identity', str(identity), str(base / source)],
                                            capture_output=True, timeout=30)
                except (OSError, subprocess.TimeoutExpired):
                    raise RuntimeError('System input decryption failed; check age and its identity') from None
                if result.returncode:
                    raise RuntimeError('System input decryption failed; check age and its identity')
                destination = private / 'policy' / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(result.stdout)
                destination.chmod(0o600)
        # Host-specific manifests retain role policy, while OS release is live.
        values = {}
        if host in {'li', 'si'}:
            import platform
            release = platform.freedesktop_os_release()
            values = {'os':'linux', 'distribution':release.get('ID',''),
                      'release':int(release.get('VERSION_ID','0').split('.')[0])}
        context = private / 'context.json'
        context.write_text(json.dumps(values))
        return subprocess.call(['sudo', '-n', '--', binary, 'files', action,
                                '--manifest', str(manifest), '--state-dir', '/var/lib/tjikup/files',
                                '--context-file', str(context)])


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        raise SystemExit(str(error))
