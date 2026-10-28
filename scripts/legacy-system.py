#!/usr/bin/env python3
"""Retired adapter: only native file operations remain available."""
from pathlib import Path
import subprocess
import sys
args = [arg for arg in sys.argv[1:] if arg != '--exclude=scripts']
if len(args) == 1 and args[0] in {'plan', 'check', 'diff', 'apply'}:
    raise SystemExit(subprocess.call([sys.executable, str(Path(__file__).with_name('system-files.py')), *args]))
raise SystemExit('Legacy rendering is retired; use native Tjikup templates and file manifests.')
