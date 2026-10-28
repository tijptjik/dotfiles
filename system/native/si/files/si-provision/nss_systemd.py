#!/usr/bin/env python3
"""Preserve local NSS policy while enabling Fedora 44 GDM shadow records."""
import argparse
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile


def render(text):
    lines = []
    seen = set()
    for line in text.splitlines(keepends=True):
        match = re.match(r"^(\s*(g?shadow)\s*:\s*)([^#\n]*)(.*)$", line.rstrip("\n"))
        if match:
            prefix, database, providers, comment = match.groups()
            seen.add(database)
            if "systemd" not in providers.split():
                gap = providers[len(providers.rstrip()):]
                line = prefix + providers.rstrip() + " systemd" + (gap or " " if comment else "") + comment + ("\n" if line.endswith("\n") else "")
        lines.append(line)
    result = "".join(lines)
    for database in ("shadow", "gshadow"):
        if database not in seen:
            result = result.rstrip("\n") + "\n" + database + ": files systemd\n"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if socket.gethostname() != "si":
        raise RuntimeError("This migration is only for si")
    target = Path("/etc/nsswitch.conf")
    original = target.read_text()
    updated = render(original)
    if updated == original:
        print("systemd shadow lookups already configured")
        return
    if not args.apply:
        print("Add systemd to shadow and gshadow lookups")
        return
    if os.geteuid() != 0 or target.is_symlink():
        raise RuntimeError("Root and an unmanaged nsswitch.conf required; use authselect for a managed symlink")
    backup = Path("/var/lib/si-provision/nss-shadow-before.conf")
    backup.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(target, backup)
    info = target.stat()
    with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, delete=False) as tmp:
        tmp.write(updated)
        os.fchmod(tmp.fileno(), info.st_mode & 0o7777)
        os.fchown(tmp.fileno(), info.st_uid, info.st_gid)
    os.replace(tmp.name, target)
    subprocess.run(["restorecon", str(target)], check=True)
    print("systemd shadow lookups configured")

if __name__ == "__main__":
    main()
