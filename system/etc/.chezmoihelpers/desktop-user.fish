# Per-user application installers must not inherit Chezetc's root HOME.
# Included at script top level so stdin contains the complete rendered hook.
if test (id -u) -eq 0
    if not set -q SUDO_USER; or test -z "$SUDO_USER"; or test "$SUDO_USER" = root
        echo "Cannot identify the desktop user; invoke chezetc through that user's wrapper." >&2
        exit 1
    end
    set -l desktop_uid (id -u "$SUDO_USER"); or exit 1
    if test "$desktop_uid" -eq 0
        exit 1
    end
    set -l desktop_home (getent passwd "$SUDO_USER" | cut -d: -f6)
    if test -z "$desktop_home"; or not test -d "$desktop_home"
        echo "Desktop home directory is unavailable." >&2
        exit 1
    end
    set -l rendered_hook (status filename)
    cd "$desktop_home"; or exit 1
    exec sudo -H -u "$SUDO_USER" \
        --preserve-env=TJIKUP_COLOR,TJIKUP_NO_SPIN,TJIKUP_REPORT_FILE,TJIKUP_COLUMNS,TJIKUP_NO_SECTIONS,TJIKUP_STATUS_LINES \
        -- env "PATH=$desktop_home/.local/bin:/usr/local/bin:/usr/bin:/bin" \
        "XDG_CONFIG_HOME=$desktop_home/.config" "XDG_DATA_HOME=$desktop_home/.local/share" \
        "XDG_CACHE_HOME=$desktop_home/.cache" "XDG_STATE_HOME=$desktop_home/.local/state" \
        /usr/bin/fish --no-config < "$rendered_hook"
end
