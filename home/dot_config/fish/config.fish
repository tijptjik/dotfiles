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

set FISHCONFIG "$HOME/.config/fish/conf.d"

# Environment Variables | FRCV
source "$FISHCONFIG/variables.fish"

# Secrets | FRCK
source "$FISHCONFIG/secrets.fish"

# Path Modifications | FRCP
source "$FISHCONFIG/paths.fish"

# Aliases | FRCA
source "$FISHCONFIG/aliases.fish"

# Functions | FRCF
source "$FISHCONFIG/utils.fish"

# Shell initialisations | FRCS
source "$FISHCONFIG/shell.fish"

# Activate UV Shell - see utils.fish
workon

# Node.js version manager
fnm env --use-on-cd --shell fish | source

# LLMTrim is scoped to Herdr. Remove only its stale inherited environment from
# ordinary shells; Herdr's launcher marks its panes so their proxy stays intact.
if not set -q HERDR_LLMTRIM
    if test "$HTTPS_PROXY" = 'http://127.0.0.1:43117'; or test "$HTTP_PROXY" = 'http://127.0.0.1:43117'
        set -e HTTPS_PROXY HTTP_PROXY ALL_PROXY https_proxy http_proxy all_proxy
        set -e NO_PROXY no_proxy
        set -e NODE_EXTRA_CA_CERTS NODE_USE_ENV_PROXY SSL_CERT_FILE CURL_CA_BUNDLE
    end
end
