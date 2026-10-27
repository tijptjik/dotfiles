#!/usr/bin/env python3
import os
if os.environ.get("FLEET_DEFER_HOOKS") == "1":
    raise SystemExit(0)
"""Keep tjikup's output and reporting environment across chezetc's sudo."""

from pathlib import Path
import re
import os
import subprocess
import tempfile


TJIKUP_ENV = (
    "TJIKUP_COLOR",
    "TJIKUP_NO_SPIN",
    "TJIKUP_REPORT_FILE",
    "TJIKUP_SKIP_PREFLIGHT",
    "TJIKUP_COLUMNS",
    "FLEET_DEFER_SYSTEM_HOOKS",
    "TJIKUP_NO_SECTIONS",
    "TJIKUP_STATUS_LINES",
)


def configure_chezetc(wrapper: Path) -> None:
    if not wrapper.is_file():
        return

    source = wrapper.read_text()
    # Extend only the upstream wrapper's explicit allowlist. Do not preserve
    # the whole environment or replace any other local wrapper customizations.
    pattern = r"(?m)^sudo --preserve-env=([A-Za-z0-9_,]+)(?= --)"
    matches = list(re.finditer(pattern, source))
    if len(matches) != 1:
        raise RuntimeError(f"unrecognized sudo environment allowlist in {wrapper}")
    match = matches[0]
    names = match.group(1).split(",")
    names.extend(name for name in TJIKUP_ENV if name not in names)
    updated = source[:match.start(1)] + ",".join(names) + source[match.end(1):]
    # The wrapper writes refresh chatter to stderr, which must stay attached
    # for sudo prompts. Suppress only these known info messages during tjikup;
    # warnings, errors, and standalone chezetc output remain visible.
    info_header = "info() {\n"
    if info_header in updated and "# tjikup: compact configuration refresh" not in updated:
        if updated.count(info_header) != 1:
            raise RuntimeError(f"ambiguous info function in {wrapper}")
        updated = updated.replace(info_header, info_header + '''    # tjikup: compact configuration refresh
    if [[ "${TJIKUP_QUIET_CONFIG:-0}" == 1 ]]; then
        case "$*" in
            "Updating file "*|"Configuration updated, please execute "*) return 0 ;;
        esac
    fi
''')
    if updated != source:
        if os.access(wrapper, os.W_OK):
            wrapper.write_text(updated)
        else:
            with tempfile.NamedTemporaryFile(mode="w") as staged:
                staged.write(updated)
                staged.flush()
                subprocess.run(["sudo", "install", "-o", "root", "-g", "root",
                                "-m", "755", staged.name, str(wrapper)], check=True)


if __name__ == "__main__":
    wrapper = Path("/opt/chezetc/chezetc")
    installer = Path.home() / ".local/share/chezetc/scripts/install-chezetc-wrapper.sh"
    if not wrapper.is_file() and installer.is_file():
        subprocess.run(["bash", str(installer)], check=True)
    configure_chezetc(wrapper if wrapper.is_file() else Path.home() / ".tools/chezetc/chezetc")
