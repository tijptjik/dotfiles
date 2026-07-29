# ~/.config/fish/conf.d/aliases.fish
# #######################
# FISH : ALIASES
# #######################

# Author : Mart van de Ven
# Contact : https://type.hk

#################################
### HYPR MODES
#################################

alias modeGame='monitor-game-mode'
alias modeDesktop='monitor-desktop-mode'

#################################
### SYSTEM TOOLS
#################################

alias df='df -h'
alias dirf='du -d 1'
alias bootlog='journalctl --boot'
alias syslog='journalctl -f'
alias top='btm'

# Suspending must leave the Wayland session alive.  Stopping UWSM after wake
# tears down Hyprland (and any active Hyprlock), returning to GDM instead of
# the locked session.
alias zzz='systemctl suspend'

#################################
### LIST
#################################

# ls, the common ones I use a lot shortened for rapid fire usage
alias l='lsd -lFh'     #size,show type,human readable
alias la='lsd -lAFh'   #long list,show almost all,show type,human readable
alias lr='lsd -tRFh'   #sorted by date,recursive,show type,human readable
alias lt='lsd -ltFh'   #long list,sorted by date,show type,human readable
alias ll='lsd -l'      #long list
alias ldot='lsd -ld .*'
alias lS='lsd -1FSsh'
alias lart='lsd -1Fcart'
alias lrt='lsd -1Fcrt'

# List only directories
alias lsdo='lsd -al | grep "^d"'

#################################
### GREP / TAIL
#################################

# turn on colours for grep
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

#################################
### HEAD / TAIL
#################################

alias h='history'
alias t='tail -f'

#################################
### DNF
#################################

alias yg='sudo dnf install -y'              # install package
alias yu='sudo dnf upgrade -y'              # system upgrade
alias yr="sudo dnf remove -y"               # remove package
alias ys="dnf search"                       # search package
alias yh='sudo dnf history'                 # command history

alias yi="dnf info"                         # show package info
alias yp='sudo dnf provides'                # file provider
alias yl="dnf list"                         # list packages
alias yli="dnf list installed"              # print all installed packages
alias ylg="dnf group list"                  # list package groups

alias ygi="sudo dnf group install -y"       # install package group
alias ygr="sudo dnf group remove -y"        # remove pagage group
alias yrl="sudo dnf remove --remove-leaves" # remove package and leaves
alias yc='sudo dnf clean packages -y'       # clean packages

#################################
### PRINTERS, PAGERS & EDITORS
#################################

# Printers
alias cat='bat --paging=never'
alias b='bat'
alias icat='kitten icat'

# Highlighting --help messages
abbr -a --position anywhere -- --help '--help | bat -plhelp'

# Pagers

# Script to open markdown in glow, fallback to bat
alias r='readr'

# Fuzzy finder
alias fzf='fzf --preview "bat --color=always --style=numbers --line-range=:500 {}"'

# Editors
alias m='micro'
alias vi='vim'
alias v='vim'
alias sv='sudo vim'
alias st='subl'
alias sublime='subl'

################################
###  GIT
################################

alias g='/usr/bin/git'
alias ga='git add --all'
alias gb='git branch'
alias gbls='git branch -a -v'
alias gbn='git checkout -b'
alias gc='git commit -v'
alias gca='git commit -a -m'
alias gcam='git commit -a -m "Minor"'
alias gcl='git clone'
alias gco='git checkout'
alias gcp='git cherry-pick'
alias gf='git fetch'
alias gff='git fetch; and git merge'
alias gl='git pull'
alias glog="git log --graph --pretty=format:'%Cred%h%Creset %an: %s - %Creset %C(yellow)%d%Creset %Cgreen(%cr)%Creset' --abbrev-commit --date=relative"
alias glogall="git log --graph --abbrev-commit --decorate --format=format:'%C(bold blue)%h%C(reset) - %C(bold green)(%ar)%C(reset) %C(white)%s%C(reset) %C(dim white)- %an%C(reset)%C(bold yellow)%d%C(reset)' --all"
alias gitlog="git log --graph --pretty=format:'%Cred%h%Creset %an: %s - %Creset %C(yellow)%d%Creset %Cgreen(%ci)%Creset' --abbrev-commit --perl-regexp --author='^((?!superdev).*)\$'"
alias gm='git merge'
alias gmm='git merge master'
alias gms='git merge staging'
alias gp='git push'
alias gra='git remote add'
alias grh='git reset HEAD'
alias grhh='git reset HEAD --hard'
alias gss='git status -s'
alias gst='git status'
alias gundo='git checkout -- .'
alias gx='git push origin (current_branch)'
alias gxnoci='git push -o ci.skip origin (current_branch)'
alias gfx='git pull upstream (current_branch); and git push upstream (current_branch)'
alias gxx='git pull origin (current_branch); and git push origin (current_branch)'
alias gz='git pull origin (current_branch)'

alias undopush="git push -f origin HEAD^:master"
alias gbcleanup='git branch --merged | grep -v "\*" | grep -v master | grep -v dev | xargs -n 1 git branch -d'

#################################
### CHEZMOI
#################################

alias cm='chezmoi'
alias ca='chezmoi add'
alias ce='chezmoi edit'
# Apply, skip externals
alias capply='chezmoi apply --exclude=externals'
# Apply, after refreshing externals
alias ceapply='chezmoi apply --refresh-externals'
# State changes, without externals
alias cdiff='chezmoi diff --exclude=externals'
# State changes, with externals
alias cediff='chezmoi diff'

################################
###  SSH
################################

alias sshs='sudo service sshd start'
alias sshstatus='sudo service sshd status'

alias sshsi='ssh -x m@ssh.type.hk'
alias sshfi='ssh -x io@192.168.1.103'
alias sshki='ssh -x io@192.168.1.101'

alias sirun='waypipe ssh m@ssh.type.hk'

################################
###  PYTHON
################################

alias p='python'

## Jupyter
# alias jbook='jupyter notebook'
# alias jlab='jupyter lab'

## Regex
# alias regex="regex_tester"

# Pelican
# alias ghpup="source activate drostehk; and ghp-import output; and gco master; and  git merge gh-pages; and git push --all; and gco source"
# alias dup="source activate drostehk; and cd $HOME/code/drostehk.github.io/output; and xdg-open http://localhost:8000/; and python -m pelican.server"

################################
###  JAVASCRIPT
################################

alias js='bun'

##############################
###  DOTFILES
################################

# Chezmoi
alias dotrc='zed $HOME/.local/share/chezmoi/'
alias sysrc='zed $HOME/.local/share/chezetc/'

# Fish
function fish_config_edit -d "Edit a {file}.fish config file"
    command chezmoi edit $HOME/.config/fish/conf.d/{$argv}.fish
    if test $status = 0
        source $HOME/.config/fish/config.fish
    end
end

alias frc='chezmoi edit $HOME/.config/fish/config.fish'
alias frca='fish_config_edit aliases'
alias frcf='fish_config_edit utils'
alias frcp='fish_config_edit paths'
alias frcs='fish_config_edit shell'
alias frcv='fish_config_edit variables'

# Hyprland
alias hrc='chezmoi edit $HOME/.config/hypr/hyprland.lua'
alias hrcl='chezmoi edit $HOME/.config/hypr/hyprlock.conf'
alias hrcp='chezmoi edit $HOME/.config/hypr/hyprpaper.conf'
alias hrcb='chezmoi edit $HOME/.config/waybar/config'

# Shells
alias zrc='chezmoi edit $HOME/.zshrc; and source ~/.zshrc'
alias brc='chezmoi edit $HOME/.bashrc; and source ~/.bashrc'

#################################
### HERDR ALIASES
#################################

function herdr -d "Run Herdr with LLMTrim enabled only for its server and panes"
    if not command -q llmtrim
        command herdr $argv
        return
    end

    if not llmtrim _alive 2>/dev/null
        command llmtrim start >/dev/null 2>&1
    end

    if not llmtrim _alive 2>/dev/null
        echo "herdr: llmtrim is unavailable; starting without the LLM proxy" >&2
        command herdr $argv
        return
    end

    # Herdr's server passes its environment to every pane. Keep LLMTrim's
    # intercepting proxy inside that boundary rather than exporting it from Fish.
    set -lx HERDR_LLMTRIM 1
    set -lx HTTPS_PROXY 'http://127.0.0.1:43117'
    set -lx HTTP_PROXY 'http://127.0.0.1:43117'
    set -lx NO_PROXY 'localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,169.254.0.0/16,fd00::/8,*.local'
    set -lx no_proxy 'localhost,127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,169.254.0.0/16,fd00::/8,*.local'
    set -lx NODE_EXTRA_CA_CERTS "$HOME/.llmtrim/ca.pem"
    set -lx NODE_USE_ENV_PROXY 1
    set -lx SSL_CERT_FILE "$HOME/.llmtrim/ca-bundle.pem"
    set -lx CURL_CA_BUNDLE "$HOME/.llmtrim/ca-bundle.pem"
    command herdr $argv
end

alias h='herdr'

# Herdr plugins keep their executables in a versioned directory rather than $PATH.
# Expose Spreader as a command and point it at its managed configuration directory.
function herdr-spreader -d "Run the installed Herdr Spreader plugin"
    set -l plugin_root (command herdr plugin list --json | command jq -r \
        '.result.plugins[] | select(.plugin_id == "herdr-spreader") | .plugin_root')

    if test -z "$plugin_root"; or not test -x "$plugin_root/target/release/herdr-spreader"
        echo "herdr-spreader: Herdr Spreader plugin is not installed" >&2
        return 127
    end

    env HERDR_PLUGIN_CONFIG_DIR="$HOME/.config/herdr/plugins/config/herdr-spreader" \
        command "$plugin_root/target/release/herdr-spreader" $argv
end

# Start the persistent Herdr server when necessary, apply the canonical layout,
# then attach to the resulting workspace.
function hup -d "Start Herdr, apply the workspace layout, and attach"
    set -l server_status (command herdr status server --json 2>/dev/null)

    if not string match -q '*"running":true*' -- "$server_status"
        command herdr server >/dev/null 2>&1 &

        for _ in (seq 1 50)
            sleep 0.1
            set server_status (command herdr status server --json 2>/dev/null)
            if string match -q '*"running":true*' -- "$server_status"
                break
            end
        end

        if not string match -q '*"running":true*' -- "$server_status"
            echo "hup: Herdr server did not start" >&2
            return 1
        end
    end

    herdr-spreader apply $argv; and command herdr
end
alias cup='codex resume --all'

## HYPE
alias h1='bun update && bun outdated'
alias h2='bun run dev'
alias h3='bun run dev:asset-service:local'
alias h4='bun run db:studio:local'
alias h5='lazygit'

## SAANSEOI
alias s1='bun run update && bun run outdated'
alias s2='bun run dev'
alias s3='bun run db:studio:meta'
alias s4='lazygit'

################################
###  ANDROID
################################

# alias adb='sudo /snap/bin/android-adb'
# alias fastboot='sudo /snap/bin/android-fastboot'

#########
# DOWNLOAD
#########

alias getyt="youtube-dl -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' (clipboard)"
alias getbc="bitchute-dl (clipboard)"

################################
# RCLONE
################################

# alias get-strippy="rclone mount crypt:/LPSY .LPSY"

################################
# FUN
################################

# Mapscii
alias maps='telnet mapscii.me'

# Star Wars : A New Hope
alias starwars='towel.blinkenlights.nl'
