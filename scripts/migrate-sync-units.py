#!/usr/bin/env python3
"""Retire old timers without ever stopping their running jobs."""
import subprocess
import sys
from pathlib import Path

OLD_UNITS = ['backup-packages', 'synctjik-device-collections-backup', 'cloudflare-restic-backup', 'private-backup', 'private-sync']

def state(unit):
    result = subprocess.run(["systemctl", "--user", "show", unit,
        "--property=LoadState,ActiveState"], capture_output=True, text=True, check=True)
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)

def legacy_units():
    root = Path.home() / ".config/systemd/user"
    return [name for name in OLD_UNITS if any((root / (name + ext)).exists()
            or (root / (name + ext)).is_symlink() for ext in [".service", ".timer"])]

def main(retire=False):
    names = OLD_UNITS if retire else legacy_units()
    # Check all jobs before altering timer state. A busy migration is retryable.
    for name in names:
        info = state(name + ".service")
        if info.get("ActiveState") in {"active", "activating", "deactivating", "reloading"}:
            print("CHECK   ! Synctjik (schedule migration)  backup running; retry after it finishes")
            return 1
    if not retire:
        print("SKIP    ✓ Synctjik (schedule migration)  " + ("ready" if names else "current"))
        return 0
    changed = False
    for name in names:
        if state(name + ".timer").get("LoadState") == "loaded":
            subprocess.run(["systemctl", "--user", "disable", "--now", name + ".timer"],
                           check=True, capture_output=True)
            changed = True
    # Cover a job that started between the first check and timer deactivation.
    for name in names:
        if state(name + ".service").get("ActiveState") in {"active", "activating", "deactivating", "reloading"}:
            print("CHECK   ! Synctjik (schedule migration)  backup running; retry after it finishes")
            return 1
    print(("CONFIG  ✓" if changed else "SKIP    ✓") + " Synctjik (schedule migration)  " +
          ("legacy timers retired" if changed else "current"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(retire="--retire" in sys.argv[1:]))
