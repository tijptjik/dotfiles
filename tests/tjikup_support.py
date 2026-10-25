"""Load the tooltjik development dependency without copying it into dotfiles."""

import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
source = os.environ.get("TOOLTJIK_REPO")
candidates = (
    [Path(source)]
    if source
    else [REPO.parent / "tooltjik", Path.home() / "code/tooltjik"]
)
for candidate in candidates:
    if (candidate / "apps/tjikup/src/tjikup").is_dir():
        sys.path.insert(0, str(candidate / "apps/tjikup/src"))
        break
# PYTHONPATH also supports source builds and the installed zipapp.
