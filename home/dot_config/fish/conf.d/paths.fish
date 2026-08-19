# ~/.config/fish/functions/paths.fish
# #############################
# FISH : PATHS
# ###############################

# Author : Mart van de Ven
# Contact : https://type.hk

#################################
### PROGRAMMING
#################################

# Python
fish_add_path $PYENV_ROOT/bin

# JavaScript
fish_add_path $BUN_INSTALL/bin
fish_add_path $FNM_PATH

# Rust
fish_add_path $HOME/.cargo/bin

# OCAML
# fish_add_path $HOME/.opam/default/bin

#################################
### CLOUD
#################################

# Google Cloud SDK - Conditionally add GCP Tools to the PATH if available
# if [ -f "$TOOLS/google-cloud-sdk/path.fish.inc" ]; source "$TOOLS/google-cloud-sdk/path.fish.inc"; end

#################################
### BLOCKCHAIN
#################################

# Solana
# fish_add_path $LOCALSHARE/solana/install/active_release/bin

#################################
### USER PATHS
#################################

# CLI Tools Root
fish_add_path $TOOLS

# CLI Tools
fish_add_path $CONFIG/rclone
fish_add_path $TOOLS/chezmoi/bin
fish_add_path $TOOLS/chezetc
fish_add_path $TOOLS/bws
fish_add_path $TOOLS/swayrec
fish_add_path $TOOLS/peco
fish_add_path $TOOLS/yt-dlp
fish_add_path $TOOLS/lokalise
fish_add_path $TOOLS/tennis

# Code
fish_add_path $HOME/code/foodworks/bin

#################################
### LOCAL BINS
#################################

# Local Bins
fish_add_path $HOME/.local/bin

# Project bins are local to the active Git worktree. They must not be added to
# `fish_user_paths`, which is universal and otherwise makes old worktrees win
# command lookup in unrelated shells.
function __fish_is_project_bin --argument-names candidate
    test -d "$candidate"; or return 1

    set -l root (command git -C (path dirname "$candidate") rev-parse --show-toplevel 2>/dev/null)
    test -n "$root"; and test (path resolve "$candidate") = (path resolve "$root/bin")
end

function __fish_prune_project_bins
    set -l cleaned_user_paths
    for path_entry in $fish_user_paths
        __fish_is_project_bin "$path_entry"; or set -a cleaned_user_paths $path_entry
    end
    set -U fish_user_paths $cleaned_user_paths

    set -l cleaned_path
    for path_entry in $PATH
        __fish_is_project_bin "$path_entry"; or set -a cleaned_path $path_entry
    end
    set -gx PATH $cleaned_path
end

function __fish_sync_project_bin --on-variable PWD
    if set -q __fish_project_bin
        set -gx PATH (string match -v -- "$__fish_project_bin" $PATH)
        set -e --global __fish_project_bin
    end

    set -l root (command git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)
    if test -n "$root"; and test -d "$root/bin"
        set -gx __fish_project_bin "$root/bin"
        set -gx PATH "$__fish_project_bin" $PATH
    end
end

__fish_prune_project_bins
__fish_sync_project_bin
