#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Use the same local development runner as the native rendering fixtures.
# Explicit overrides let CI and release checks select their own build.
export TJIKUP_BINARY="${TJIKUP_BINARY:-$HOME/code/tjikos/apps/tjikup/target/debug/tjikup}"
if [[ ! -x "$TJIKUP_BINARY" ]]; then
    echo "[ERROR] Set TJIKUP_BINARY to an executable Tjikup build: $TJIKUP_BINARY" >&2
    exit 1
fi

echo "[CHECK] Python syntax"
python3 - <<'PY'
import ast
from pathlib import Path

for path in (path for root in ("native", "scripts") for path in Path(root).rglob("*")):
    if path.is_file() and (path.suffix == ".py" or path.read_bytes().splitlines()[0:1] == [b"#!/usr/bin/env python3"]):
        ast.parse(path.read_text(), filename=str(path))
PY

echo "[CHECK] Bash and Fish syntax (non-template files)"
while IFS= read -r -d '' script; do
    case "$(head -n 1 "$script")" in
        *bash*|*'/bin/sh') bash -n "$script" ;;
        *fish*) fish --no-config --no-execute "$script" ;;
        *)
            if [[ "$script" == *.fish ]]; then
                fish --no-config --no-execute "$script"
            fi
            ;;
    esac
done < <(find native scripts -type f ! -name '*.tmpl' ! -name '*.j2' \( -name '*.sh' -o -name '*.fish' -o -path 'native/home/files/.local/bin/*' \) -print0)

echo "[CHECK] Native task templates"
python3 scripts/check-task-templates.py

echo "[CHECK] Regression tests"
python3 -B -m unittest discover -s tests -v

echo "[SUCCESS] Validation passed."
