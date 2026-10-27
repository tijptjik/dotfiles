#!/usr/bin/env python3
"""Commands referenced by this fleet's tjikup.json; not a standalone runner."""

import sys
from tjikup_dependency import check_runtime

if not check_runtime():
    raise SystemExit(1)

from fleet_update import main
from fleet_update.core import UpdateError

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UpdateError as error:
        print(f"fleet-update: {error}", file=sys.stderr)
        raise SystemExit(1)
