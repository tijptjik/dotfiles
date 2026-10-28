"""Adopt matching native credentials without invoking a legacy template engine."""
import os
from pathlib import Path
import stat
from native_adoption import adopt as native_adopt


def adopt(repo, manifest, state, binary):
    token = Path.home() / '.config/bws/environment'
    if token.exists() or token.is_symlink():
        info = token.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError('Bitwarden token must be a regular file owned by this user')
        token.chmod(0o600)
    native_adopt(manifest, state, [binary, 'files', 'apply', '--manifest', str(manifest), '--state-dir', str(state)])
