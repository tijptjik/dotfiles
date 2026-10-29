#!/usr/bin/env python3
"""Run related asset steps with one result and private per-step diagnostics."""
import argparse
import os
from pathlib import Path
import re
import subprocess

def execute(kind, run_dir):
    steps = {
        "fonts": [
            ["python3", str(run_dir / "home-run_before_71-consolidate-user-fonts.py")],
            ["fish", "--no-config", str(run_dir / "home-run_after_72-refresh-user-fonts.fish")],
        ],
        "icons": [
            ["fish", "--no-config", str(run_dir / "home-run_after_36-tjikup-icon-cache.fish")],
            ["fish", "--no-config", str(run_dir / "home-run_after_40-rose-punk-icons.fish")],
        ],
    }[kind]
    title = "Fonts" if kind == "fonts" else "Rose Punk icons"
    changed = False
    log = run_dir / (kind + "-steps.log")
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as private:
        for index, command in enumerate(steps):
            result = subprocess.run(command, capture_output=True, text=True,
                env={**os.environ, "TJIKUP_REPORT_FILE": str(run_dir / (kind + "-step-" + str(index) + ".report"))})
            private.write(result.stdout + result.stderr)
            private.flush()
            if result.returncode:
                print("FAIL    ✗ " + title + "  setup failed; see private step log")
                return result.returncode
            lines = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
            verbs = re.findall(r"^(SKIP|CHECK|UPDATE|INSTALL|CONFIG|SYNC|APPLY)\s", lines, re.M)
            changed |= any(verb not in ("SKIP", "CHECK") for verb in verbs)
    print(("APPLY   ✓ " if changed else "SKIP    ✓ ") + title +
          ("  updated" if changed else "  current"))
    return 0

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["fonts", "icons"])
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    return execute(args.kind, args.run_dir)

if __name__ == "__main__":
    raise SystemExit(main())
