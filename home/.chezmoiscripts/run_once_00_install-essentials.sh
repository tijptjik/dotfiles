#!/bin/bash
# Essential packages installer for chezmoi initialization
# This script installs the basic packages needed for dotfiles management

set -euo pipefail

# Update package manager
echo "[INSTALL] System Updates..."
sudo dnf update -y

# Install essential packages
echo
echo "[INSTALL] Essential packages..."
sudo dnf install -y sudo kitty fish git chezmoi age
