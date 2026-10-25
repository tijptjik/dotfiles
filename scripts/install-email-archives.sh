#!/usr/bin/env bash
# Install only this tool; do not apply unrelated Chezmoi changes or hooks.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="$(mktemp -d)"
trap 'rm -rf -- "$build_dir"' EXIT
(
    cd "$repo_dir/scripts/email_archive_tui"
    go build -trimpath -o "$build_dir/email-archives-tree" .
)
install -d -m 755 "$HOME/.local/lib/email-archives" "$HOME/.local/bin"
for module in email_archive_annual email_archive_index email_archive_export email_archive_run email_archive_live email_archives; do
    install -m 644 "$repo_dir/scripts/$module.py" "$HOME/.local/lib/email-archives/$module.py"
done
install -m 755 "$build_dir/email-archives-tree" "$HOME/.local/bin/email-archives-tree"
install -m 755 "$repo_dir/home/dot_local/bin/executable_email-archives" "$HOME/.local/bin/email-archives"
