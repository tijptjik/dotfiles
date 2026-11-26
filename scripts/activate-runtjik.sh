#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
check_only=0
case "${1:-}" in
    --check) check_only=1 ;;
    "") ;;
    *) echo "Usage: $0 [--check]" >&2; exit 2 ;;
esac
if (( check_only )); then
    "${TJIKUP_BINARY:-tjikup}" workflow --repo "$repo_dir" desktop cleanup --check
else
    "${TJIKUP_BINARY:-tjikup}" workflow --repo "$repo_dir" desktop cleanup --apply
fi
"$HOME/.local/bin/runtjik" check
