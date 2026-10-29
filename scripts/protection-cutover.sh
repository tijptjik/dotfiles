#!/usr/bin/env bash
# Keep worker checks and lock handling in Synctjik, policy in Dotjik.
set -euo pipefail
scope="${1:?home or system required}"; shift
[[ "${1:-}" == -- ]] && shift
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
host="$(hostname -s)"
policy="$repo/native/protection-migration/$scope-$host.json"
if [[ ! -f "$policy" ]]; then exec "$@"; fi
if [[ "$scope" == system ]]; then
    [[ "$EUID" == 0 ]] || { echo "Run the reviewed root file apply with its prepared inputs under the system guard." >&2; exit 1; }
    exec /usr/local/bin/synctjik protection-migration --policy "$policy" -- "$@"
fi
exec "${SYNCTJIK_BINARY:-$HOME/.local/bin/synctjik}" protection-migration --policy "$policy" -- "$@"
