#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[CHECK] Bash scripts"
bash -n setup.sh
bash -n scripts/validate.sh
bash -n etc/.chezmoiscripts/run_00-header.sh

echo "[CHECK] Fish scripts"
while IFS= read -r script; do
    sed '/^{{/d' "$script" | fish --no-config --no-execute
done < <(find etc/.chezmoiscripts etc/.chezmoitemplates etc/.chezmoihelpers -type f \( -name '*.fish' -o -name '*.fish.tmpl' \) | sort)

echo "[CHECK] Native task templates for Fi/Li/Si"
python3 ../scripts/check-task-templates.py

echo "[CHECK] Setup regressions"
python3 -B -m unittest discover -s tests -v

echo "[SUCCESS] Validation passed."
