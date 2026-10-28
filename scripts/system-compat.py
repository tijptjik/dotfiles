#!/usr/bin/env python3
"""Compatibility entry point: file operations use the unified Tjikup policy."""
from pathlib import Path
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]
args = sys.argv[1:] or ['plan']
if args == ['source-path']:
    print(repo / 'system/etc')
    raise SystemExit(0)
if args[0] in {'check', 'plan', 'diff', 'apply'} and len(args) == 1:
    raise SystemExit(subprocess.call([sys.executable, str(repo / 'scripts/native-files.py'), 'system', *args]))
if args[0] in {'data', 'execute-template', 'cat', 'managed', 'target-path'}:
    raise SystemExit(subprocess.call([sys.executable, str(repo / 'scripts/legacy-system.py'), *args]))
raise SystemExit('Use tjikup for tasks; chezetc/systjik support check, plan, diff, apply (files only), and legacy read commands.')
