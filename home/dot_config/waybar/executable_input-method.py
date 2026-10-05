#!/usr/bin/env python3
"""Report Fcitx's active method, including changes made inside applications."""

import html
import json
import configparser
from pathlib import Path
import subprocess
import sys

METHODS = {
    "keyboard-us-altgr-intl": ("EN", "English — US International (AltGr accents)", "english"),
    "keyboard-us-intl": ("EN", "English — US International (dead keys)", "english"),
    "pinyin": ("拼", "Pinyin — Traditional Chinese", "pinyin"),
    "quick-classic": ("速", "Quick (速成) — Traditional Chinese", "quick"),
    "quick3": ("速", "Quick 3 (速成) — Traditional Chinese", "quick"),
    "cantonese": ("粵", "Cantonese", "cantonese"),
    "keyboard-us": ("EN", "English — US", "english"),
    "keyboard-gb": ("EN", "English — UK", "english"),
}


def remote(*args):
    return subprocess.run(
        ["fcitx5-remote", "--check", *args],
        check=True, capture_output=True, text=True, timeout=2,
    ).stdout.strip()


def main():
    try:
        current = remote("-n")
        if sys.argv[1:] == ["cycle"]:
            # Respect the selected group, including groups edited in the GUI.
            profile = configparser.ConfigParser(interpolation=None)
            profile.read(Path.home() / ".config/fcitx5/profile")
            group = remote("-q")
            prefix = next(
                section for section in profile.sections()
                if section.startswith("Groups/") and section.count("/") == 1
                and profile[section].get("Name", "").strip('"') == group
            ) + "/Items/"
            sections = sorted(
                (section for section in profile.sections() if section.startswith(prefix)),
                key=lambda section: int(section.rsplit("/", 1)[1]),
            )
            methods = [profile[section]["Name"].strip('"') for section in sections]
            if not methods:
                return
            index = methods.index(current) if current in methods else -1
            remote("-s", methods[(index + 1) % len(methods)])
            return
        text, name, css = METHODS.get(current, (current or "—", current, "other"))
        tooltip = name
    except (OSError, subprocess.SubprocessError, configparser.Error, StopIteration, KeyError, ValueError):
        text, tooltip, css = "—", "Fcitx 5 is unavailable", "unavailable"
    print(json.dumps({"text": text, "tooltip": html.escape(tooltip), "class": css}))


if __name__ == "__main__":
    main()
