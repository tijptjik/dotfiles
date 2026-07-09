#!/usr/bin/env fish

set -l bws_env_file "$HOME/.config/bws/environment"
set -l chezmoi_key_file "$HOME/.keys/chezmoi.txt"
set -l bws_executable "$HOME/.tools/bws/bws"

if not test -x "$bws_executable"; and not command -v -q bws
    echo "Bitwarden Secrets Manager CLI is not available. Run chezmoi apply once to bootstrap it." >&2
    exit 1
end

if not test -r "$bws_env_file"
    echo "Bitwarden environment is missing at $bws_env_file. Run ~/.local/share/chezmoi/home/.bitwarden-setup.fish." >&2
    exit 1
end

if not test -r "$chezmoi_key_file"
    echo "chezmoi age identity is missing at $chezmoi_key_file. Run ~/.local/share/chezmoi/home/.bitwarden-setup.fish." >&2
    exit 1
end
