# Node.js version manager
#
# Keep path setup here; config.fish owns the single fnm environment
# initialization so it can enable --use-on-cd without creating a second
# multishell link.
set -gx FNM_DIR "$HOME/.local/share/fnm"
fish_add_path "$FNM_DIR"
