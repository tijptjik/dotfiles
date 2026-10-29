"""Fleet icon identities shared by terminal rendering and asset generation."""
import json
from pathlib import Path

DOCKER_SERVICES = json.loads(Path(__file__).with_name("docker-services.json").read_text())
# Use one-cell Nerd Font glyphs followed by a space, so titles stay aligned.
SERVICE_ICONS = {
    "Zoom Workplace": "\uf03d", "ChatGPT Desktop": "\uf075",
    "Applications": "\uf1b2", "Assets": "\uf187", "Bartjik": "\uf2d0",
    "Systjik": "\uf013", "Dotjik": "\uf015", "Codex Desktop": "\uf121",
    "Codex LB": "\uf121", "Collie": "\uf0c1", "Docker": "\uf308",
    "Fedora": "\uf30a", "Flatpak": "\uf49c", "Google Chrome stable": "\uf268",
    "GDM": "\uf361",
    "Gitfetch": "\ue702", "Greetjik": "\uf075", "Herdr": "\uf12e",
    "Hyprvoice": "\uf130", "Launcher": "\uf135", "Media": "\uf008",
    "Mullvad": "\uf132", "Nginx": "\ue776", "Notjik": "\uf0f3",
    "Notifications": "\uf0f3", "NSS": "\uf023", "Obsidian": "\ue275", "oo7": "\uf084",
    "Power": "\uf011", "Prowlarr": "\uf002",
    "Python": "\ue73c", "Runtjik": "\uf120", "Rust": "\ue7a8", "SnapRAID": "\uf1c0",
    "Storage": "\uf0a0", "Strata": "\uf279", "Sublime Text": "\ue7aa", "Systemd": "\uf085",
    "Tailscale": "\uf0e8", "Telegram": "\uf1d8", "Terminal": "\uf120",
    "Tippecanoe": "\uf279", "Tjikup": "\uf021", "Transmission": "\uf019",
    "Vite": "\uf0e7", "Zed": "\uf044", "llmtrim": "\uf0c4",
    "Bitwarden": "\uf132", "Fish": "\uf489", "UV": "\ue73c", "FNM": "\ue718",
    "Gum": "\uf120", "Bun": "\ue76f", "Solaar": "\uf185", "Fcitx": "\uf11c",
    "Codex": "\uf121", "Zapzap": "\uf232", "Gtk-bookmarks": "\uf02e",
    "Local Changes": "\ue702", "Templates": "\ue702", "Home and system": "\uf085",
    "Dotjik": "\uf015", "Systjik": "\uf013", "tjikOS": "\uf021",
    "dotjik": "\uf015", "systjik": "\uf013", "tjikos": "\uf021",
}
ASSET_ICONS = {"fonts": "\uf031", "font folder migration": "\uf031", "user fonts": "\uf031",
               "icon cache": "\uf00a", "Rose Punk icons": "\uf00a",
               "symbolic link icon": "\uf0c1"}
SPRITE_ALIASES = {"Assets (symbolic link icon)": "Assets (icon cache)"}
SERVICE_ICONS.update({name: entry["glyph"] for name, entry in DOCKER_SERVICES.items()})
SERVICE_ICONS.update({"Plex": "\uf04b", "Docker images": "\uf308"})



DISPLAY_NAMES = {
    "llmtrim": "Llmtrim", "Google Chrome stable": "Google Chrome Stable",
    "Gtk-bookmarks": "GTK Bookmarks", "Zapzap": "ZapZap",
}


def display_title(label):
    """Title case display labels while preserving brands, acronyms and IDs."""
    service, separator, subtype = label.partition(" (")
    if service not in SERVICE_ICONS:
        return label

    def title(value):
        minor = {"and", "of", "for", "to", "the"}
        return " ".join(word if not word.islower() or (index and word in minor)
                        else word.capitalize()
                        for index, word in enumerate(value.split(" ")))

    result = DISPLAY_NAMES.get(service, title(service))
    return result + (separator + title(subtype) if separator else "")
