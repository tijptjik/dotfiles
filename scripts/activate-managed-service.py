#!/usr/bin/env python3
"""One reporting owner for desktop activation and changed-runtime refresh."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    app = sys.argv[1]
    if app not in {"bartjik", "notjik"}:
        raise SystemExit("Unsupported managed desktop service")
    activation = ["bash", str(ROOT / "scripts" / ("activate-" + app + ".sh"))]
    checked = subprocess.run([*activation, "--check"], capture_output=True)
    if checked.returncode not in (0, 1):
        return checked.returncode
    changed = checked.returncode == 1
    if changed:
        result = subprocess.run(activation, capture_output=True)
        if result.returncode:
            print("FAIL    ✗ " + app.title() + "  activation failed")
            return result.returncode
    result = subprocess.run([sys.executable, str(ROOT / "scripts/refresh-user-services.py"),
                             "--unit", app + ".service"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith(("__stage_", "__tjikup_section__")):
            continue
        print(line)
    if result.returncode:
        return result.returncode
    if not result.stdout.strip() or all(line.startswith("__") for line in result.stdout.splitlines()):
        print(("ACTIVATE ✓ " if changed else "SKIP    ✓ ") + app.title() +
              ("  activated" if changed else "  already active"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
