#!/usr/bin/env fish

# Check if herdr binary is available, install if not
if not command -v herdr >/dev/null 2>&1
    echo "[INSTALL] Herdr..."
    curl -fsSL https://herdr.dev/install.sh | sh
end
