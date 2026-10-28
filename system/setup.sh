#!/usr/bin/env bash
# The consolidated repository owns setup; this installs the runner, not packages.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ ! -f "$repo_dir/tjikup.json" || ! -f "$repo_dir/scripts/install-tjikup.sh" ]]; then
    echo 'Use the system/ directory inside the dotfiles checkout.' >&2
    exit 1
fi
bash "$repo_dir/scripts/install-tjikup.sh"
bash "$repo_dir/system/scripts/install-chezetc-wrapper.sh"
