#!/usr/bin/env fish

set -l script_dir (dirname (status --current-filename))
set -l install_script "$script_dir/.chezmoiscripts/run_once_before_01-install-bws.fish"
set -l setup_script "$script_dir/.chezmoiscripts/run_once_before_02-setup-bitwarden.fish"

fish "$install_script"
if test $status -ne 0
    echo "Error running $install_script" >&2
    exit 1
end

fish "$setup_script"
if test $status -ne 0
    echo "Error running $setup_script" >&2
    exit 1
end
