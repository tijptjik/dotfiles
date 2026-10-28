#!/usr/bin/env bash
set -euo pipefail
profile="${XDG_CONFIG_HOME:-$HOME/.config}/synctjik/device.json"
# Existing devices retain their policy; cold bootstrap explicitly enrolls new ones.
[[ -f "$profile" ]] || exit 0
case "${1:-}" in
    check) exec synctjik ready ;;
    apply) synctjik setup; synctjik ready; synctjik schedule ;;
    *) exit 2 ;;
esac
