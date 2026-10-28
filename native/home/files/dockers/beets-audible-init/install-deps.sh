#!/bin/bash
set -euo pipefail

# Keep the plugin and Beets versions compatible across container recreation.
if /lsiopy/bin/python3 - <<'PY'
from importlib.metadata import PackageNotFoundError, version
expected = {
    "beets": "2.14.1",
    "beets-audible": "1.7.1",
    "beets-copyartifacts3": "0.1.7",
}
try:
    assert all(version(name) == wanted for name, wanted in expected.items())
except (PackageNotFoundError, AssertionError):
    raise SystemExit(1)
PY
then
    echo "Audiobook plugin dependencies already installed."
else
    /lsiopy/bin/python3 -m pip install --no-cache-dir \
        'beets==2.14.1' 'beets-audible==1.7.1' 'beets-copyartifacts3==0.1.7'
fi
