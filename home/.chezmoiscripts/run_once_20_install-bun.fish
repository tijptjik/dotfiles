#!/usr/bin/env fish

echo "[INSTALL] Bun..."

# Set up logging based on whether we're running interactively
if status is-interactive
    # Interactive mode - just print to stdout
    function log
        echo $argv
    end
else
    # Non-interactive mode (cron) - pipe to systemd-cat
    function log
        echo $argv | systemd-cat -t install-bun
    end
end


# Check if bun binary is available, install if not
if not command -v bun >/dev/null 2>&1
    log "bun not found, installing..."
    curl -fsSL https://bun.com/install | bash
else
    log "bun is already installed"
end
