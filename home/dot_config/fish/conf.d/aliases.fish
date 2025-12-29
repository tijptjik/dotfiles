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

alias zzz='sudo systemctl suspend && uwsm stop'

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
### PAGERS & EDITORS
#################################

alias m='micro'
alias vi='vim'
alias v='vim'
alias sv='sudo vim'
alias st='subl'
alias sublime='subl'

alias b='bat'

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
# alias dup="source activate drostehk; and cd /home/io/code/drostehk.github.io/output; and xdg-open http://localhost:8000/; and python -m pelican.server"

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
alias hrc='chezmoi edit $HOME/.config/hypr/hyprland.conf'
alias hrcl='chezmoi edit $HOME/.config/hypr/hyprlock.conf'
alias hrcp='chezmoi edit $HOME/.config/hypr/hyprpaper.conf'
alias hrcb='chezmoi edit $HOME/.config/waybar/config'

# Shells
alias zrc='chezmoi edit $HOME/.zshrc; and source ~/.zshrc'
alias brc='chezmoi edit $HOME/.bashrc; and source ~/.bashrc'

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
