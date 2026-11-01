# Managed SDK; preserve explicit SDK choices for other projects.
if not set -q ANDROID_HOME
    set -gx ANDROID_HOME "$HOME/.local/share/android-sdk"
end
if test -d "$ANDROID_HOME/platform-tools"
    fish_add_path --path "$ANDROID_HOME/platform-tools" "$ANDROID_HOME/cmdline-tools/22.0/bin"
end
