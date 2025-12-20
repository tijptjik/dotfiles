#!/usr/bin/env fish

# Ensure bws is installed and available.
if not command -v bws >/dev/null 2>&1
    set BWS_EXECUTABLE "$HOME/.tools/bws/bws"
    if test -f "$BWS_EXECUTABLE"
        set -gx PATH "$HOME/.tools/bws" $PATH
    else
        echo "Bitwarden Secrets Manager CLI (bws) not found."
        exit 1
    end
end

# --- User Configuration ---
# TODO: Replace this with the actual URL to your encrypted access token.
set ENCRYPTED_TOKEN_URL "https://pub-05ad430ac346452fa7d511c8e383383f.r2.dev/bws-token.age"

# TODO: Replace this with the Secret ID of your chezmoi key from Bitwarden.
set CHEZMOI_KEY_SECRET_ID "efb21803-dbaa-425e-8762-b3b00077af36"
# --------------------------

# --- Main Logic ---

set -l bws_config_dir "$HOME/.config/bws"
set -l bws_config_file "$bws_config_dir/environment"
set -l chezmoi_key_file "$HOME/.keys/chezmoi.txt"
set -l keys_dir "$HOME/.keys"

# --- Handle Bitwarden Access Token ---
if test -f "$bws_config_file"
    # Load the token from the file into the current environment
    for line in (cat "$bws_config_file")
        if string match -q '*=*' "$line"
            set -l parts (string split -m 1 '=' "$line")
            if test "$parts[1]" = "BWS_ACCESS_TOKEN"
                set -gx BWS_ACCESS_TOKEN "$parts[2]"
            end
        end
    end
else
    echo "Bitwarden access token missing. Fetching and decrypting..."

    # Create a temporary file to securely handle the downloaded token
    set encrypted_token_file (mktemp)
    if not curl -fsSL -o "$encrypted_token_file" "$ENCRYPTED_TOKEN_URL"
        echo "Error: Failed to download the encrypted access token from $ENCRYPTED_TOKEN_URL"
        rm -f "$encrypted_token_file"
        exit 1
    end

    # Decrypt the token, will be prompted for a passphrase.
    set DECRYPTED_TOKEN (age -d "$encrypted_token_file")

    # Check for decryption errors
    if test $status -ne 0
        echo "Error: Failed to decrypt the access token. Please check your passphrase."
        rm -f "$encrypted_token_file"
        exit 1
    end

    # Clean up the temporary file immediately after use
    rm -f "$encrypted_token_file"

    # Export the token for the current session.
    set -gx BWS_ACCESS_TOKEN "$DECRYPTED_TOKEN"
    echo "Successfully decrypted BWS_ACCESS_TOKEN."

    # Persist the token for subsequent runs and for the wrapper script.
    mkdir -p "$bws_config_dir"
    echo "BWS_ACCESS_TOKEN=$DECRYPTED_TOKEN" > "$bws_config_file"
    echo "Persisted BWS_ACCESS_TOKEN to $bws_config_file"
end

# --- Handle chezmoi Decryption Key ---
if not test -f "$chezmoi_key_file"
    # Check if we have the access token before proceeding
    if test -z "$BWS_ACCESS_TOKEN"
        echo "Error: BWS_ACCESS_TOKEN is not set. Cannot fetch chezmoi key."
        exit 1
    end

    echo "Fetching chezmoi key from Bitwarden Secrets Manager..."
    mkdir -p "$keys_dir"
    # Use printf for safety with multi-line keys
    set -l CHEZMOI_KEY (bws secret get $CHEZMOI_KEY_SECRET_ID | jq -r '.value')
    if test $status -ne 0; or test -z "$CHEZMOI_KEY"
        echo "Failed to retrieve chezmoi key using bws."
        exit 1
    end
    printf '%s\n' "$CHEZMOI_KEY" > "$chezmoi_key_file"
    echo "chezmoi key successfully written to $chezmoi_key_file"
end
