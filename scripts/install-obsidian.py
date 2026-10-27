#!/usr/bin/env python3
"""Install the official Obsidian AppImage without replacing user profiles."""
import hashlib
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'home/.chezmoitemplates'))
from github_api import github_json


def release_asset(release, machine):
    version = release['tag_name'].removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Expected a stable Obsidian release')
    suffix = {'x86_64': '', 'aarch64': '-arm64'}[machine]
    name = f'Obsidian-{version}{suffix}.AppImage'
    asset = next(a for a in release['assets'] if a['name'] == name)
    expected_url = f'https://github.com/obsidianmd/obsidian-releases/releases/download/v{version}/{name}'
    if asset['browser_download_url'] != expected_url:
        raise ValueError('Unexpected Obsidian download source')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', asset.get('digest') or ''):
        raise ValueError('Official release has no SHA-256 digest')
    return asset


def verified(path, asset):
    if not path.is_file() or path.stat().st_size != asset['size']:
        return False
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return 'sha256:' + digest == asset['digest']


def install(home, asset):
    directory = home / '.local/opt/obsidian'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / asset['name']
    changed = False
    if not verified(target, asset):
        with tempfile.NamedTemporaryFile(dir=directory, suffix='.download', delete=False) as stream:
            temporary = Path(stream.name)
        try:
            subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                            '--retry', '3', '--connect-timeout', '20', '--max-time', '600',
                            '--output', str(temporary), asset['browser_download_url']], check=True)
            if not verified(temporary, asset):
                raise ValueError('Obsidian AppImage checksum or size mismatch')
            temporary.chmod(0o755)
            temporary.replace(target)
            changed = True
        finally:
            temporary.unlink(missing_ok=True)
    target.chmod(0o755)
    link = home / '.local/bin/obsidian-appimage'
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.is_symlink() and link.exists():
        raise ValueError(f'Refusing to overwrite non-symlink {link}')
    if not link.is_symlink() or link.resolve() != target.resolve():
        temporary_link = link.with_name(f'.obsidian-appimage-{os.getpid()}')
        try:
            temporary_link.symlink_to(target)
            temporary_link.replace(link)
        finally:
            temporary_link.unlink(missing_ok=True)
        changed = True
    return changed


def main():
    release = github_json('https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest')
    changed = install(Path.home(), release_asset(release, platform.machine()))
    print('__stage_note__:' + ('updated' if changed else 'no changes'))


if __name__ == '__main__':
    main()
