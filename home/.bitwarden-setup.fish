#!/usr/bin/env fish

set -l script_dir (dirname (status --current-filename))
set -l install_script "$script_dir/.chezmoitemplates/install-bitwarden-cli.py"
set -l setup_template "$script_dir/.chezmoiscripts/run_once_before_02-setup-bitwarden.fish.tmpl"

python3 "$install_script"
if test $status -ne 0
    echo "Error running $install_script" >&2
    exit 1
end

# Bootstrap before chezmoi init installs the hook that requires these secrets.
set -l setup_script (mktemp); or exit 1
chezmoi --config /dev/null --config-format toml --source "$script_dir" execute-template < "$setup_template" > "$setup_script"
if test $status -ne 0
    rm -f "$setup_script"
    echo "Error rendering $setup_template" >&2
    exit 1
end
fish "$setup_script"
set -l result $status
rm -f "$setup_script"
exit $result
