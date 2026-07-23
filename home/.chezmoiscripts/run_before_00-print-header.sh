#!/bin/bash
if [ "${CHEZMOI_SKIP_SPLASH:-0}" = "1" ]; then
  exit 0
fi

rainbow_ascii() {
  local text="$1"
  local index=0
  local position
  local character
  local -a colors=(196 208 226 46 39 129)

  for ((position = 0; position < ${#text}; position++)); do
    character="${text:position:1}"
    if [ "$character" = $'\n' ] || [ "$character" = ' ' ]; then
      printf '%s' "$character"
      continue
    fi

    printf '\033[1;38;5;%sm%s' "${colors[index]}" "$character"
    index=$(( (index + 1) % ${#colors[@]} ))
  done

  printf '\033[0m'
}

if [ "${1:-}" = "tjikup" ] && [ -t 1 ]; then
  rainbow_ascii '
    _   _        ____  ____  ____
 __| | / |  ____|_  _||   _||_   |
|__  || |__|____|/  \ |  |_   || |
   |_| \___|    |_/\_||____|  \__/
'
  echo
fi

if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
  echo
  gum style --bold --foreground 13 "Tijpfiles"
  gum style --foreground 8 "https://github.com/tijptjik/dotfiles"
  echo
  exit 0
fi

echo "_____ ___    _ ____ _____   _ ___ _  __
|_   _|_ _|  | |  _ \_   _| | |_ _| |/ /
  | |  | |_  | | |_) || |_  | || || ' /
  | |  | | |_| |  __/ | | |_| || || . \\
  |_| |___\___/|_|    |_|\___/|___|_|\_\\
"
echo "https://github.com/tijptjik/dotfiles"
echo
