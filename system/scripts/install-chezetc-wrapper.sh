#!/usr/bin/env bash
# Retain the familiar command without installing a second configuration engine.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
sudo install -m 0755 "$script_dir/chezetc-launcher.sh" /usr/local/bin/chezetc
