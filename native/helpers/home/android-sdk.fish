#!/usr/bin/env fish
# Managed Linux SDK for API 35 builds. Google archive checksum from
# https://developer.android.com/studio (command-line tools 22.0, build 15859902).
set -l sdk "$HOME/.local/share/android-sdk"
set -l tools "$sdk/cmdline-tools/22.0"
set -l digest 4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583

function sdk_ready --argument-names sdk tools
    test -x "$tools/bin/sdkmanager"; and test -s "$tools/lib/sdkmanager-classpath.jar"; and test -s "$sdk/platforms/android-35/android.jar"; and test -x "$sdk/build-tools/35.0.0/aapt2"; and test -x "$sdk/build-tools/35.0.0/apksigner"; and test -x "$sdk/platform-tools/adb"
end
if test "$argv[1]" = --check
    sdk_ready "$sdk" "$tools"
    exit $status
end
if test (uname -s) != Linux; or test (uname -m) != x86_64
    echo 'Android SDK policy requires Linux x86_64' >&2
    exit 1
end
set -gx JAVA_HOME /usr/lib/jvm/temurin-21-jdk
if not test -x "$JAVA_HOME/bin/java"
    echo 'Install managed temurin-21-jdk before Android SDK' >&2
    exit 1
end
mkdir -p "$sdk/cmdline-tools"; or exit $status
if test "$argv[1]" != --locked
    exec flock "$sdk/.install.lock" fish --no-config (status filename) --locked
end
set -gx ANDROID_HOME "$sdk"
set -l cache "$HOME/.cache/tjikup/android-sdk"
if set -q XDG_CACHE_HOME
    set cache "$XDG_CACHE_HOME/tjikup/android-sdk"
end
if not test -x "$tools/bin/sdkmanager"; or not test -s "$tools/lib/sdkmanager-classpath.jar"
    mkdir -p "$cache"; or exit $status
    set -l archive "$cache/commandlinetools-linux-15859902.zip"
    if not printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status 2>/dev/null
        set -l download (mktemp "$cache/download.XXXXXX"); or exit $status
        if not curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --output "$download" https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip
            rm -f "$download"
            exit 1
        end
        if not printf '%s  %s\n' "$digest" "$download" | sha256sum --check --status
            rm -f "$download"
            echo 'Android command-line tools checksum mismatch' >&2
            exit 1
        end
        mv -f "$download" "$archive"; or exit $status
    end
    set -l stage (mktemp -d "$sdk/cmdline-tools/.install.XXXXXX"); or exit $status
    if not unzip -q "$archive" -d "$stage"
        rm -rf "$stage"
        exit 1
    end
    if not test -x "$stage/cmdline-tools/bin/sdkmanager"; or not test -s "$stage/cmdline-tools/lib/sdkmanager-classpath.jar"
        rm -rf "$stage"
        echo 'Incomplete Android command-line tools archive' >&2
        exit 1
    end
    # Preserve any damaged previous installation for recovery.
    if test -e "$tools"
        mv "$tools" "$stage/previous"; or exit $status
    end
    mv "$stage/cmdline-tools" "$tools"; or exit $status
    if not test -e "$stage/previous"
        rmdir "$stage"
    end
end
if test "$TJIKUP_OPERATION" != update; and sdk_ready "$sdk" "$tools"
    echo 'Android SDK API 35 available'
    exit 0
end
# Install only the declared build dependencies. sdkmanager presents the Google
# SDK license for these packages; enrollment in this policy accepts it locally.
yes | "$tools/bin/sdkmanager" --sdk_root="$sdk" --install 'platform-tools' 'platforms;android-35' 'build-tools;35.0.0'
or exit $status
sdk_ready "$sdk" "$tools"; or exit 1
echo 'Android SDK API 35 and Build Tools 35.0.0 ready'
