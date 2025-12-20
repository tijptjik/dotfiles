#!/usr/bin/env fish

set -l bws_env_file "$HOME/.config/bws/environment"

# If the bws environment file exists, load the variables from it.
if test -f "$bws_env_file"
    # Read each line, split by '=', and set the environment variable.
    # This is a fish-idiomatic way to parse a .env file.
    for line in (cat "$bws_env_file")
        if string match -q '*=*' "$line"
            set -l parts (string split -m 1 '=' "$line")
            set -gx "$parts[1]" "$parts[2]"
        end
    end
end

# Find the real bws executable. We assume it's in the PATH.
# The installer script should have put it in ~/.tools/bws.
set -l bws_executable (command -v $HOME/.tools/bws/bws || command -v bws)
if test -z "$bws_executable"
    echo "Error: bws executable not found." >&2
    exit 1
end

# Execute the real bws command with all forwarded arguments.
exec "$bws_executable" $argv
