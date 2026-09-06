#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[CHECK] Python syntax"
python3 - <<'PY'
import ast
from pathlib import Path

for path in Path("home").rglob("*"):
    if path.is_file() and (path.suffix == ".py" or path.name == "executable_tjikup"):
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
done < <(find home scripts -type f ! -name '*.tmpl' \( -name '*.sh' -o -name '*.fish' -o -path 'home/dot_local/bin/*' \) -print0)

echo "[CHECK] Tjikup regressions"
python3 -B -m unittest discover -s tests -v

echo "[SUCCESS] Validation passed."
