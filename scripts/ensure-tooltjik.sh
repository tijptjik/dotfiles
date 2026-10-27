#!/usr/bin/env bash
# Source this helper, then call ensure_tooltjik with the required app file.
ensure_tooltjik() {
    local required="$1" managed=0
    tool_repo="${TOOLTJIK_REPO:-}"
    if [[ -z "$tool_repo" ]]; then
        if [[ -e "$HOME/code/tooltjik/.git" ]]; then
            tool_repo="$HOME/code/tooltjik"
        else
            tool_repo="$HOME/.local/share/tooltjik"
            managed=1
        fi
    fi
    if [[ ! -e "$tool_repo/.git" ]]; then
        mkdir -p -- "$(dirname -- "$tool_repo")"
        LC_ALL=C git clone --progress https://github.com/tijptjik/tooltjik.git "$tool_repo" || return
    elif [[ ! -f "$tool_repo/$required" && "$managed" == 1 ]]; then
        # Upgrade an older bootstrap checkout, without overwriting local work.
        local changes
        changes="$(git -C "$tool_repo" status --porcelain)" || return
        if [[ -n "$changes" ]]; then
            echo "Cannot update $tool_repo: checkout has local changes." >&2
            return 1
        fi
        LC_ALL=C git -C "$tool_repo" pull --ff-only --progress || return
    fi
    if [[ ! -f "$tool_repo/$required" ]]; then
        echo "Update $tool_repo to a revision containing $required." >&2
        return 1
    fi
}
