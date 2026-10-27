#!/usr/bin/env bash
# Source this helper, then call ensure_tooltjik with the required app file.
ensure_tooltjik() {
    local required="$1"
    tool_repo="${TOOLTJIK_REPO:-}"
    if [[ -z "$tool_repo" ]]; then
        tool_repo="$HOME/code/tooltjik"
        if [[ ! -e "$tool_repo" && ! -L "$tool_repo" &&
              ( -e "$HOME/.local/share/tooltjik" || -L "$HOME/.local/share/tooltjik" ) ]]; then
            echo "Move $HOME/.local/share/tooltjik to $tool_repo before retrying (see docs/tjikup.md)." >&2
            return 1
        fi
    fi
    if [[ ! -e "$tool_repo/.git" ]]; then
        mkdir -p -- "$(dirname -- "$tool_repo")"
        LC_ALL=C git clone --progress git@github.com:tijptjik/tooltjik.git "$tool_repo" || return
    fi
    if [[ ! -f "$tool_repo/$required" ]]; then
        echo "Update $tool_repo to a revision containing $required." >&2
        return 1
    fi
}
