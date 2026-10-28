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

CHEZETC_CONFIG="${CHEZETC_CONFIG:-$HOME/.config/chezetc/chezetc.toml}"
if command -v chezmoi >/dev/null 2>&1 && [[ -f "$CHEZETC_CONFIG" ]]; then
    echo "[CHECK] Rendered chezmoi Fish templates"
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' EXIT

    while IFS= read -r script; do
        rendered="$tmpdir/$(basename "$script" .tmpl)"
        chezmoi --source "$PWD/etc" --config "$CHEZETC_CONFIG" execute-template < "$script" > "$rendered"
        fish --no-config --no-execute "$rendered"
    done < <(find etc/.chezmoiscripts -type f -name '*.fish.tmpl' | sort)
else
    echo "[SKIP] Rendered templates require chezmoi and $CHEZETC_CONFIG"
fi

echo "[CHECK] Setup regressions"
python3 -B -m unittest discover -s tests -v

echo "[SUCCESS] Validation passed."
