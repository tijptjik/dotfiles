#!/usr/bin/env bash
set -euo pipefail
profile="${XDG_CONFIG_HOME:-$HOME/.config}/synctjik/device.json"
# Existing devices retain their policy; cold bootstrap explicitly enrolls new ones.
if [[ ! -f "$profile" ]]; then
    printf '%s\n' 'SKIP    - Synctjik (required archives)  no archive collections enrolled'
    exit 0
fi
case "${1:-}" in
    check) exec synctjik ready ;;
    apply) synctjik setup; synctjik ready; synctjik schedule ;;
    *) exit 2 ;;
esac
