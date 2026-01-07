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
