# ~/.config/fish/config.fish
################################
## FISH CONFIG
#################################

# Author : Mart van de Ven
# Contact : https://type.hk

# #######################
# LOGIN
# #######################

if status --is-login
    if test (tty) = /dev/tty1
        exec start-hyprland
    end
end

# #######################
# INCLUDES
# #######################

# Fish loads conf.d automatically before this file. Do not source it twice.

# Activate UV Shell - see utils.fish
workon

# Node.js version manager
if command -q fnm
    fnm env --use-on-cd --shell fish | source
end

# `workon` and fnm can restore an inherited PATH after paths.fish has run.
# Apply its worktree-bin cleanup once shell initialisation is complete.
__fish_prune_project_bins
__fish_sync_project_bin

# LLMTrim is scoped to Herdr. Remove only its stale inherited environment from
# ordinary shells; Herdr's launcher marks its panes so their proxy stays intact.
if not set -q HERDR_LLMTRIM
    if test "$HTTPS_PROXY" = 'http://127.0.0.1:43117'; or test "$HTTP_PROXY" = 'http://127.0.0.1:43117'
        set -e HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy
        set -e NO_PROXY no_proxy
        set -e NODE_EXTRA_CA_CERTS NODE_USE_ENV_PROXY SSL_CERT_FILE CURL_CA_BUNDLE
    end
end
