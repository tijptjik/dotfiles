#!/usr/bin/env sh
# tinted-shell (https://github.com/tinted-theming/tinted-shell)
# Scheme name: Rosé Punk
# Scheme author: Tijptjik
# Template author: Tinted Theming (https://github.com/tinted-theming)
export BASE24_THEME="rose-punk"

color00="19/17/24" # Base 00 - Black
color01="eb/6f/92" # Base 08 - Red
color02="31/74/8f" # Base 0B - Green
color03="f4/b7/b5" # Base 0A - Yellow
color04="71/88/ff" # Base 0D - Blue
color05="ff/53/a6" # Base 0E - Magenta
color06="9c/cf/d8" # Base 0C - Cyan
color07="e5/e5/e5" # Base 05 - White
color08="55/51/69" # Base 03 - Bright Black
color09="ff/6b/95" # Base 12 - Bright Red
color10="2f/87/ab" # Base 14 - Bright Green
color11="fa/cd/cc" # Base 13 - Bright Yellow
color12="85/96/ed" # Base 16 - Bright Blue
color13="e5/6e/a1" # Base 17 - Bright Magenta
color14="9b/df/eb" # Base 15 - Bright Cyan
color15="f5/f5/f7" # Base 07 - Bright White
color16="f6/c1/77" # Base 09
color17="c0/34/5c" # Base 0F
color18="1f/1d/2e" # Base 01
color19="26/23/3a" # Base 02
color20="6e/6a/86" # Base 04
color21="ec/eb/ef" # Base 06
color_foreground="e5/e5/e5" # Base 05
color_background="19/17/24" # Base 00


if [ -z "$TTY" ] && ! TTY=$(tty) || [ ! -w "$TTY" ]; then
  put_template() { true; }
  put_template_var() { true; }
  put_template_custom() { true; }
elif [ -n "$TMUX" ] || [ "${TERM%%[-.]*}" = "tmux" ]; then
  # Tell tmux to pass the escape sequences through
  # (Source: http://permalink.gmane.org/gmane.comp.terminal-emulators.tmux.user/1324)
  put_template() { printf '\033Ptmux;\033\033]4;%d;rgb:%s\033\033\\\033\\' "$@" > "$TTY"; }
  put_template_var() { printf '\033Ptmux;\033\033]%d;rgb:%s\033\033\\\033\\' "$@" > "$TTY"; }
  put_template_custom() { printf '\033Ptmux;\033\033]%s%s\033\033\\\033\\' "$@" > "$TTY"; }
elif [ "${TERM%%[-.]*}" = "screen" ]; then
  # GNU screen (screen, screen-256color, screen-256color-bce)
  put_template() { printf '\033P\033]4;%d;rgb:%s\007\033\\' "$@" > "$TTY"; }
  put_template_var() { printf '\033P\033]%d;rgb:%s\007\033\\' "$@" > "$TTY"; }
  put_template_custom() { printf '\033P\033]%s%s\007\033\\' "$@" > "$TTY"; }
elif [ "${TERM%%-*}" = "linux" ]; then
  put_template() { [ "$1" -lt 16 ] && printf "\e]P%x%s" "$1" "$(echo "$2" | sed 's/\///g')" > "$TTY"; }
  put_template_var() { true; }
  put_template_custom() { true; }
else
  put_template() { printf '\033]4;%d;rgb:%s\033\\' "$@" > "$TTY"; }
  put_template_var() { printf '\033]%d;rgb:%s\033\\' "$@" > "$TTY"; }
  put_template_custom() { printf '\033]%s%s\033\\' "$@" > "$TTY"; }
fi

# 16 color space
put_template 0  "$color00"
put_template 1  "$color01"
put_template 2  "$color02"
put_template 3  "$color03"
put_template 4  "$color04"
put_template 5  "$color05"
put_template 6  "$color06"
put_template 7  "$color07"
put_template 8  "$color08"
put_template 9  "$color09"
put_template 10 "$color10"
put_template 11 "$color11"
put_template 12 "$color12"
put_template 13 "$color13"
put_template 14 "$color14"
put_template 15 "$color15"

# foreground / background / cursor color
if [ -n "$ITERM_SESSION_ID" ]; then
  # iTerm2 proprietary escape codes
  put_template_custom Pg e5e5e5 # foreground
  put_template_custom Ph 191724 # background
  put_template_custom Pi e5e5e5 # bold color
  put_template_custom Pj 26233a # selection color
  put_template_custom Pk e5e5e5 # selected text color
  put_template_custom Pl e5e5e5 # cursor
  put_template_custom Pm 191724 # cursor text
else
  put_template_var 10 "$color_foreground"
  if [ "$BASE24_SHELL_SET_BACKGROUND" != false ]; then
    put_template_var 11 "$color_background"
    if [ "${TERM%%-*}" = "rxvt" ]; then
      put_template_var 708 "$color_background" # internal border (rxvt)
    fi
  fi
  put_template_custom 12 ";7" # cursor (reverse video)
fi

# clean up
unset put_template
unset put_template_var
unset put_template_custom
unset color00
unset color01
unset color02
unset color03
unset color04
unset color05
unset color06
unset color07
unset color08
unset color09
unset color10
unset color11
unset color12
unset color13
unset color14
unset color16
unset color17
unset color18
unset color19
unset color20
unset color21
unset color15
unset color_foreground
unset color_background

# Optionally export variables
if [ -n "$TINTED_SHELL_ENABLE_BASE24_VARS" ]; then
  export BASE24_COLOR_00_HEX="191724"
  export BASE24_COLOR_01_HEX="1f1d2e"
  export BASE24_COLOR_02_HEX="26233a"
  export BASE24_COLOR_03_HEX="555169"
  export BASE24_COLOR_04_HEX="6e6a86"
  export BASE24_COLOR_05_HEX="e5e5e5"
  export BASE24_COLOR_06_HEX="ecebef"
  export BASE24_COLOR_07_HEX="f5f5f7"
  export BASE24_COLOR_08_HEX="eb6f92"
  export BASE24_COLOR_09_HEX="f6c177"
  export BASE24_COLOR_0A_HEX="f4b7b5"
  export BASE24_COLOR_0B_HEX="31748f"
  export BASE24_COLOR_0C_HEX="9ccfd8"
  export BASE24_COLOR_0D_HEX="7188ff"
  export BASE24_COLOR_0E_HEX="ff53a6"
  export BASE24_COLOR_0F_HEX="c0345c"
  export BASE24_COLOR_10_HEX="110f18"
  export BASE24_COLOR_11_HEX="08080c"
  export BASE24_COLOR_12_HEX="ff6b95"
  export BASE24_COLOR_13_HEX="facdcc"
  export BASE24_COLOR_14_HEX="2f87ab"
  export BASE24_COLOR_15_HEX="9bdfeb"
  export BASE24_COLOR_16_HEX="8596ed"
  export BASE24_COLOR_17_HEX="e56ea1"
fi
