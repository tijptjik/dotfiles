#!/usr/bin/env fish

# Check if bun binary is available, install if not
if not command -v fnm >/dev/null 2>&1
    echo "[INSTALL] FNM..."
    curl -fsSL https://fnm.vercel.app/install | bash
end
