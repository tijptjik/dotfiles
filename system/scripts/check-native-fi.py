#!/usr/bin/env python3
"""Compare Fi's native candidate with Chezetc, without changing live targets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root, entries):
    result = {}
    for entry in entries:
        path = root / entry['path'].lstrip('/')
        if not os.path.lexists(path):
            result[entry['path']] = {'kind': 'absent'}
            continue
        info = path.lstat()
        row = {'kind': 'symlink' if path.is_symlink() else 'file',
               'uid': info.st_uid, 'gid': info.st_gid,
               'inode': info.st_ino, 'mtime_ns': info.st_mtime_ns}
        if path.is_symlink():
            row['target'] = os.readlink(path)
        else:
            row.update(mode=stat.S_IMODE(info.st_mode), sha256=digest(path))
        result[entry['path']] = row
    return result


def call(command, allowed=(0,)):
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode not in allowed:
        raise RuntimeError(f'Command failed ({result.returncode}): {command[0]}\n{result.stderr}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tjikup', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--legacy-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('run with sudo: isolated ownership validation requires root')
    manifest = args.manifest.resolve()
    spec = json.loads(manifest.read_text())
    entries = spec['entries']
    output = args.output.resolve()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    root = output / 'root'
    root.mkdir()
    before_live = inventory(Path('/'), entries)
    legacy = ['chezmoi', '--config', str(args.legacy_config.resolve()),
              '--persistent-state', str(output / 'legacy-state.boltdb'),
              '--cache', str(output / 'legacy-cache')]
    targets = call([*legacy, 'managed', '--include=files,symlinks', '--path-style=absolute']).stdout.splitlines()
    if set(targets) != {entry['path'] for entry in entries}:
        raise RuntimeError('native manifest and legacy target sets differ')
    native = [str(args.tjikup.resolve()), 'files']
    options = ['--manifest', str(manifest), '--root', str(root), '--state-dir', str(output / 'state')]
    first = call([*native, 'apply', *options])
    first_snapshot = inventory(root, entries)
    comparisons = []
    for entry in entries:
        name = entry['path']
        target = root / name.lstrip('/')
        expected = call([*legacy, 'cat', name]).stdout.encode()
        if entry['kind'] == 'file':
            equivalent = target.read_bytes() == expected
        elif entry['kind'] == 'symlink':
            equivalent = os.readlink(target) == expected.decode().rstrip('\n')
        else:
            equivalent = not expected and not os.path.lexists(target)
        if not equivalent:
            raise RuntimeError(f'native rendering differs from Chezetc: {name}')
        if entry['kind'] != 'absent':
            info = target.lstat()
            if (info.st_uid, info.st_gid) != (entry['uid'], entry['gid']):
                raise RuntimeError(f'ownership mismatch: {name}')
            if entry['kind'] == 'file' and stat.S_IMODE(info.st_mode) != int(entry['mode'], 8):
                raise RuntimeError(f'mode mismatch: {name}')
        comparisons.append({'path': name, 'legacy_equivalent': True})
    state = output / 'state' / (spec['id'] + '.json')
    state_before = (state.read_bytes(), state.stat().st_mtime_ns, state.stat().st_ino)
    second = call([*native, 'apply', *options])
    call([*native, 'check', *options])
    if first_snapshot != inventory(root, entries):
        raise RuntimeError('repeat apply changed target content, metadata or timestamps')
    if state_before != (state.read_bytes(), state.stat().st_mtime_ns, state.stat().st_ino):
        raise RuntimeError('repeat apply rewrote deployment state')
    # This is a read-only plan against /, using a separate nonexistent state path.
    live_plan = call([*native, 'plan', '--manifest', str(manifest), '--state-dir', str(output / 'live-state'), '--json'], allowed=(0, 1, 2))
    if (output / 'live-state').exists():
        raise RuntimeError('read-only plan created state')
    if before_live != inventory(Path('/'), entries):
        raise RuntimeError('live files changed while verification ran')
    report = {'manifest_sha256': digest(manifest), 'binary_sha256': digest(args.tjikup),
              'comparisons': comparisons, 'first_apply': first.stdout.strip(),
              'second_apply': second.stdout.strip(), 'repeat_apply_preserved_inodes_and_timestamps': True,
              'live_files_unchanged': True, 'live_plan_exit': live_plan.returncode,
              'live_plan': json.loads(live_plan.stdout), 'snapshot': first_snapshot}
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(comparisons)} targets match Chezetc; repeat apply changed nothing.')
    print(f'Live read-only plan exit: {live_plan.returncode}; live files unchanged.')
    print(f'Evidence: {output / "verification.json"}')


if __name__ == '__main__':
    main()
