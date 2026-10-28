#!/usr/bin/env fish

set -l script_dir (dirname (status --current-filename))
set -l install_script "$script_dir/.chezmoitemplates/install-bitwarden-cli.py"

python3 "$install_script"
if test $status -ne 0
    echo "Error running $install_script" >&2
    exit 1
end

# The runner is installed before credential bootstrap; no template engine is needed.
fish "$script_dir/../native/tasks/bootstrap/setup-bitwarden.fish"
exit $status
