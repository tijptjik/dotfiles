#!/usr/bin/env python3
"""Capture explicitly supported live settings before file application."""
import argparse
from pathlib import Path
from fleet_capture import capture
from device_policy import profile
import socket

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dry-run', action='store_true')
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
if profile() and socket.gethostname() not in {'fi', 'li', 'si'}:
    print('SKIP    - Capture live settings  new device has no enrolled capture sources')
    raise SystemExit(0)
raise SystemExit(capture(args.repo, dry_run=args.dry_run))
