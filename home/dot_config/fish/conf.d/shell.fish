# ~/.config/fish/functions/shell.fish
# #############################
# FISH : SHELL
# ###############################

# Author : Mart van de Ven
# Contact : https://type.hk

# Prompt
starship init fish | source

# Profile
direnv hook fish | source

# FNM
source $HOME/.config/fish/conf.d/fnm.fish

# FZF
fzf_configure_bindings --history=\cr --directory=\cf --processes=\cp --variables=\ce --git_log=\e\cr --git_status=\e\cs
set fzf_diff_highlighter diff-so-fancy
set fzf_preview_dir_cmd lsd
