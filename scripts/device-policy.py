#!/usr/bin/env python3
"""Template role query and cold-bootstrap configuration entry point."""
from pathlib import Path
import sys
from device_policy import configure, context

repo = Path(__file__).resolve().parents[1]
if sys.argv[1:] == ['role']:
    print(context(repo)['role'])
elif sys.argv[1:] == ['configure']:
    configure(repo)
else:
    raise SystemExit('usage: device-policy.py role|configure')
