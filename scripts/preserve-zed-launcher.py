#!/usr/bin/env python3
"""Keep native-owned launchers intact around Zed's upstream installer."""
import argparse
import json
import socket
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


def vendor_launcher(home, channel):
    suffix = '' if channel == 'stable' else '-' + channel
    appid = 'dev.zed.Zed' + ('' if channel == 'stable' else '-' + channel.capitalize())
    app = home / ('.local/zed' + suffix + '.app')
    source = app / 'share/applications' / (appid + '.desktop')
    if not source.is_file():
        source = app / 'share/applications' / ('zed' + suffix + '.desktop')
    # Match the two substitutions made by upstream's installer, including TryExec.
    return source.read_bytes().replace(b'Icon=zed', ('Icon=' + str(app / 'share/icons/hicolor/512x512/apps/zed.png')).encode()).replace(
        b'Exec=zed', ('Exec=' + str(app / 'bin/zed')).encode())


def is_managed(repo, home, channel):
    base = repo / 'native/home'
    manifest = base / ('files-' + socket.gethostname() + '.json')
    if not manifest.is_file():
        manifest = base / 'files-device.json'
    spec = json.loads(manifest.read_text())
    entries = list(spec.get('entries', []))
    for source in spec.get('entries_files', []):
        entries.extend(json.loads((base / source).read_text()))
    appid = 'dev.zed.Zed' + ('' if channel == 'stable' else '-' + channel.capitalize())
    target = str(home / '.local/share/applications' / (appid + '.desktop'))
    return any(entry['path'].replace('{{ user.home }}', str(home)) == target
               and not entry.get('when') for entry in entries)


def run(home, channel, command):
    appid = 'dev.zed.Zed' + ('' if channel == 'stable' else '-' + channel.capitalize())
    target = home / '.local/share/applications' / (appid + '.desktop')
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'tjikup/zed-launchers'
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='install-', dir=state))
    before = None
    if target.exists() or target.is_symlink():
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise RuntimeError('Zed launcher must be a regular file owned by the invoking user')
        before = target.read_bytes()
        shutil.copy2(target, backup / target.name)
    code = subprocess.call(command)
    if target.is_symlink():
        raise RuntimeError(f'Zed launcher changed to a symlink; preserved backup: {backup}')
    after = target.read_bytes() if target.exists() else None
    if after == before:
        return code
    if after is not None and after != vendor_launcher(home, channel):
        raise RuntimeError(f'Unexpected launcher edit during Zed installation; preserved backup: {backup}')
    if before is None:
        # A fresh native install applies its own launcher after installing Zed.
        target.unlink(missing_ok=True)
    else:
        fd, temporary = tempfile.mkstemp(prefix='.zed-launcher-', dir=target.parent)
        os.close(fd)
        try:
            shutil.copy2(backup / target.name, temporary)
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', choices=['stable', 'preview', 'nightly'], required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('installer command required')
    try:
        home = Path.home()
        if is_managed(Path(__file__).resolve().parents[1], home, args.channel):
            raise SystemExit(run(home, args.channel, command))
        raise SystemExit(subprocess.call(command))
    except (OSError, RuntimeError) as error:
        raise SystemExit(str(error))
