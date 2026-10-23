#!/usr/bin/env python3
"""Consolidate legacy user fonts without overwriting differing files."""
import argparse
import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess


def same(a, b):
    if a.is_symlink() or b.is_symlink():
        return a.is_symlink() and b.is_symlink() and os.readlink(a) == os.readlink(b)
    if a.is_dir() or b.is_dir():
        return a.is_dir() and b.is_dir()
    return hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()


def consolidate(home, apply=False):
    old = home / '.fonts'
    target = home / '.local/share/fonts'
    if target.is_symlink():
        raise RuntimeError('Canonical font directory must not be a symlink')
    if old.is_symlink():
        if old.resolve() != target.resolve():
            raise RuntimeError('Legacy font symlink points elsewhere')
        return 'Fonts already consolidated'
    if old.exists() and not old.is_dir():
        raise RuntimeError('Legacy font path is not a directory')
    entries = sorted(old.rglob('*')) if old.exists() else []
    conflicts = []
    for source in entries:
        dest = target / source.relative_to(old)
        if (dest.exists() or dest.is_symlink()) and not same(source, dest):
            conflicts.append(str(source.relative_to(old)))
    if conflicts:
        raise RuntimeError('Font conflicts require review: ' + ', '.join(conflicts))
    if not apply:
        return f'Fonts ready to consolidate: {len(entries)} entries; no conflicts'
    target.mkdir(parents=True, exist_ok=True)
    for source in entries:
        dest = target / source.relative_to(old)
        if dest.exists() or dest.is_symlink():
            continue
        if source.is_symlink():
            dest.symlink_to(os.readlink(source))
        elif source.is_dir():
            dest.mkdir(mode=source.stat().st_mode & 0o777)
        else:
            shutil.copy2(source, dest)
    # Verify before replacing the legacy directory, preserving a rollback copy.
    if any(not same(source, target / source.relative_to(old)) for source in entries):
        raise RuntimeError('Font verification failed; legacy directory retained')
    backup = None
    if old.exists():
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        backup = home / '.local/state/font-migration' / stamp / 'fonts'
        backup.parent.mkdir(parents=True, mode=0o700)
        old.rename(backup)
    old.symlink_to('.local/share/fonts')
    return f'Fonts consolidated; rollback: {backup or "not needed"}'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--status-helper', type=Path)
    args = parser.parse_args()
    try:
        result = consolidate(Path.home(), args.apply)
        if args.status_helper and shutil.which('fish'):
            unchanged = result == 'Fonts already consolidated'
            subprocess.run(['fish', '--no-config', '-c',
                            'source $argv[1]; status_msg $argv[2..-1]', '--',
                            str(args.status_helper), 'SKIP' if unchanged else 'SYNC',
                            '✓', 'User fonts', 'no changes' if unchanged else result], check=True)
        else:
            print(result)
    except RuntimeError as exc:
        parser.exit(1, str(exc) + '\n')
