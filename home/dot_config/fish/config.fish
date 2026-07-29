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

# #######################
# LLMTRIM
# #######################

# >>> llmtrim >>>
if command -q llmtrim; and llmtrim _alive 2>/dev/null
    set -gx HTTPS_PROXY 'http://127.0.0.1:43117'
    set -gx HTTP_PROXY 'http://127.0.0.1:43117'
    set -gx NO_PROXY 'localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,169.254.0.0/16,fd00::/8,*.local'
    set -gx no_proxy 'localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,169.254.0.0/16,fd00::/8,*.local'
    set -gx NODE_EXTRA_CA_CERTS '/home/io/.llmtrim/ca.pem'
    set -gx NODE_USE_ENV_PROXY '1'
    set -gx SSL_CERT_FILE '/home/io/.llmtrim/ca-bundle.pem'
    set -gx CURL_CA_BUNDLE '/home/io/.llmtrim/ca-bundle.pem'
end
# <<< llmtrim <<<
