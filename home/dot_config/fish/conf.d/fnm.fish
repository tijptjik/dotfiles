# Node.js version manager
#
# Fish automatically loads every file in conf.d once per shell. Keep this as the
# only fnm initialization so each shell owns a single disposable multishell link.
set -gx FNM_DIR "$HOME/.local/share/fnm"
fish_add_path "$FNM_DIR"

# Zed and other tools frequently launch `fish -c` helpers. They do not need a
# per-shell Node selection, and running `fnm env` there would leak a link each
# time. Interactive terminals retain the normal fnm behavior.
if status is-interactive
    fnm env --shell fish | source
end
