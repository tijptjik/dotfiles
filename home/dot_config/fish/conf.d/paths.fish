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

# Code
fish_add_path $HOME/code/foodworks/bin

#################################
### LOCAL BINS
#################################

# Local Bins
fish_add_path $HOME/.local/bin

# Respect local bins
fish_add_path ./bin
