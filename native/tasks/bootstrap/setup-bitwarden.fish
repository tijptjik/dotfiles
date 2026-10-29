#!/usr/bin/env fish
set -l repo_dir (path resolve (dirname (status --current-filename))/../../..)
source "$repo_dir/native/helpers/home/status.fish"

# Ensure bws is installed and available.
if not command -v bws >/dev/null 2>&1
    set BWS_EXECUTABLE "/usr/local/bin/bws"
    if test -f "$BWS_EXECUTABLE"
        set -gx PATH "/usr/local/bin" $PATH
    else
        status_msg FAILED "✗" "Bitwarden Secrets Manager CLI"
        echo "Bitwarden Secrets Manager CLI (bws) not found."
        exit 1
    end
end

# --- User Configuration ---
# Encrypted bootstrap credential source.
set ENCRYPTED_TOKEN_URL "https://pub-05ad430ac346452fa7d511c8e383383f.r2.dev/bws-token.age"

# TODO: Replace this with the Secret ID of the age identity from Bitwarden.
set AGE_KEY_SECRET_ID "efb21803-dbaa-425e-8762-b3b00077af36"
# --------------------------

# --- Main Logic ---

set -l bws_config_dir "$HOME/.config/bws"
set -l bws_config_file "$bws_config_dir/environment"
set -l age_key_file "$HOME/.keys/age.txt"
set -l keys_dir "$HOME/.keys"
umask 077

# --- Handle Bitwarden Access Token ---
if test -f "$bws_config_file"
    chmod 600 "$bws_config_file"; or exit 1
    # Load the token from the file into the current environment
    for line in (cat "$bws_config_file")
        if string match -q '*=*' "$line"
            set -l parts (string split -m 1 '=' "$line")
            if test "$parts[1]" = "BWS_ACCESS_TOKEN"
                set -gx BWS_ACCESS_TOKEN "$parts[2]"
            end
        end
    end
    status_msg CONFIG "✓" "Bitwarden access token"
else
    interactive_stage "Bitwarden access token" CONFIG "Bitwarden access token" fish -c '
        set encrypted_token_file (mktemp)
        if not curl -fsSL -o "$encrypted_token_file" "$argv[1]"
            rm -f "$encrypted_token_file"
            exit 1
        end

        set DECRYPTED_TOKEN (age -d "$encrypted_token_file")
        if test $status -ne 0
            rm -f "$encrypted_token_file"
            exit 1
        end

        rm -f "$encrypted_token_file"
        mkdir -p "$argv[2]"
        echo "BWS_ACCESS_TOKEN=$DECRYPTED_TOKEN" > "$argv[3]"
        chmod 600 "$argv[3]"
    ' "$ENCRYPTED_TOKEN_URL" "$bws_config_dir" "$bws_config_file"

    for line in (cat "$bws_config_file")
        if string match -q '*=*' "$line"
            set -l parts (string split -m 1 '=' "$line")
            if test "$parts[1]" = "BWS_ACCESS_TOKEN"
                set -gx BWS_ACCESS_TOKEN "$parts[2]"
            end
        end
    end
end

# --- Handle age Decryption Key ---
if not test -f "$age_key_file"
    # Check if we have the access token before proceeding
    if test -z "$BWS_ACCESS_TOKEN"
        status_msg FAILED "✗" "age decryption key"
        echo "BWS_ACCESS_TOKEN is not set. Cannot fetch age key."
        exit 1
    end

    stage "age decryption key" CONFIG "age decryption key" fish -c '
        mkdir -p "$argv[2]"
        set -l AGE_KEY (bws secret get "$argv[1]" | jq -r ".value")
        if test $status -ne 0; or test -z "$AGE_KEY"
            exit 1
        end
        printf "%s\n" (string unescape $AGE_KEY) > "$argv[3]"
        chmod 600 "$argv[3]"
    ' "$AGE_KEY_SECRET_ID" "$keys_dir" "$age_key_file"
else
    status_msg CONFIG "✓" "age decryption key"
end
