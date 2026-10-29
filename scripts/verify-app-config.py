#!/usr/bin/env python3
"""Verify an updated app's native configuration and refresh only active units."""
import os
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
    print('CHECK   ✓ ' + app + ' (Configuration)  verified', flush=True)
    if app in UNITS:
        return subprocess.call([sys.executable, str(ROOT / 'refresh-user-services.py'),
                                *[arg for unit in UNITS[app] for arg in ['--unit', unit]]],
                               env={**os.environ, 'TJIKUP_HIDE_UNCHANGED_SERVICES': '1', 'TJIKUP_SERVICE_SECTION': 'Verification'})
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
