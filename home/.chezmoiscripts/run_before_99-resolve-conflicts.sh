#!/bin/bash
if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
  echo
  gum style --bold --foreground 11 "RESOLVE CONFLICTS"
  exit 0
fi

echo
echo "RESOLVE CONFLICTS"
