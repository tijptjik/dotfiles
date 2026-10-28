#!/usr/bin/env python3
"""Verify an updated app's native configuration and refresh only active units."""
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
UNITS = {'notjik': ['notjik.service', 'notjik-telegram.service'], 'bartjik': ['bartjik.service'], 'hyprvoice': ['hyprvoice.service'], 'codex-lb': ['codex-lb.service']}

def main():
    app = sys.argv[1]
    code = subprocess.call([sys.executable, str(ROOT / 'home-files.py'), 'check', '--group', app])
    if code:
        print('CHECK   ! ' + app + ' configuration  needs attention; run tjikup --apply-dotfiles')
        return code
    if app in UNITS:
        return subprocess.call([sys.executable, str(ROOT / 'refresh-user-services.py'),
                                *[arg for unit in UNITS[app] for arg in ['--unit', unit]]])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
