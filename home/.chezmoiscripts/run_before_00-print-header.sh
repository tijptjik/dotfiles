#!/bin/bash
if [ "${CHEZMOI_SKIP_SPLASH:-0}" = "1" ]; then
  exit 0
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
