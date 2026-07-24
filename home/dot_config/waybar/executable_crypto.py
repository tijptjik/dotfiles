#!/usr/bin/env python3

"""Adapt the legacy crypto module's output for the Waybar layout."""

import json
import subprocess
import sys
from pathlib import Path


LEGACY_MODULE = Path.home() / ".config" / "waybar" / "crypto" / "waybar_crypto.py"
# The legacy module uses three normal spaces between coins. Replacing the last
# one with a hair space reduces that separator by 4 px at the bar's 14 px font.
COIN_SEPARATOR = "  \u200a"


def main() -> None:
    result = subprocess.run([str(LEGACY_MODULE)], capture_output=True, text=True)
    if result.returncode:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)

    payload = json.loads(result.stdout)
    payload["text"] = payload["text"].replace("   ", COIN_SEPARATOR)
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
