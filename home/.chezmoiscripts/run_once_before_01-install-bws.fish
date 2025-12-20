#!/usr/bin/env fish

set BWS_DIR "$HOME/.tools/bws"
set BWS_EXECUTABLE "$BWS_DIR/bws"

if test -f "$BWS_EXECUTABLE"
    # Ensure it's in the path
    if not contains "$BWS_DIR" $fish_user_paths
        set -Ua fish_user_paths "$BWS_DIR"
        echo "Added $BWS_DIR to fish_user_paths."
    end
    exit 0
end

echo "[INSTALL] Bitwarden Secrets Manager..."

# Create target directory
mkdir -p "$BWS_DIR"

# Create a temporary directory for the download
set TMP_DIR (mktemp -d)

# Download the zip file
set BWS_ZIP_URL "https://github.com/bitwarden/sdk-sm/releases/download/bws-v1.0.0/bws-x86_64-unknown-linux-gnu-1.0.0.zip"
set BWS_ZIP_PATH "$TMP_DIR/bws.zip"

echo "Downloading bws from $BWS_ZIP_URL..."
if not curl -fL -o "$BWS_ZIP_PATH" "$BWS_ZIP_URL"
    echo "Failed to download bws."
    rm -rf "$TMP_DIR"
    exit 1
end

# Extract the zip file
echo "Extracting bws..."
if not unzip -q "$BWS_ZIP_PATH" -d "$TMP_DIR"
    echo "Failed to extract bws. 'unzip' might not be installed."
    rm -rf "$TMP_DIR"
    exit 1
end

# Find the executable and move it
set EXTRACTED_BWS (find "$TMP_DIR" -type f -name bws)
if test -z "$EXTRACTED_BWS"
    echo "Could not find 'bws' executable in the archive."
    rm -rf "$TMP_DIR"
    exit 1
end

mv "$EXTRACTED_BWS" "$BWS_EXECUTABLE"
chmod +x "$BWS_EXECUTABLE"

# Clean up
rm -rf "$TMP_DIR"

echo "bws installed successfully to $BWS_EXECUTABLE"

# Add to path
if not contains "$BWS_DIR" $fish_user_paths
    set -Ua fish_user_paths "$BWS_DIR"
    echo "Added $BWS_DIR to fish_user_paths."
end
