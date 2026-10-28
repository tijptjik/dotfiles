#!/bin/sh
# Compatibility only; system policy now belongs to the dotfiles checkout.
exec python3 "${DOTJIK_REPO:-${XDG_DATA_HOME:-$HOME/.local/share}/dotjik}/scripts/system-compat.py" "$@"
