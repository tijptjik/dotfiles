#!/usr/bin/env python3
"""Select a Rose Punk icon direction in dotfiles and the current GTK session."""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
THEMES = {'a': 'rose-punk', 'b': 'rose-punk-illustrated'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', choices=THEMES, help='a: outline; b: illustrated')
    args = parser.parse_args()
    theme = THEMES[args.version]
    source = ROOT / 'home/dot_local/share/icons' / theme
    if not (source / 'index.theme').exists():
        parser.error(f'{theme} artwork is not installed in this checkout yet')
    settings = ROOT / 'home/dot_config/gtk-4.0/settings.ini'
    settings.write_text(re.sub(r'^gtk-icon-theme-name=.*$', 'gtk-icon-theme-name=' + theme,
                              settings.read_text(), flags=re.M))
    dconf = ROOT / 'home/dot_config/dconf/interface.conf'
    dconf.write_text(re.sub(r"^icon-theme=.*$", "icon-theme='" + theme + "'",
                           dconf.read_text(), flags=re.M))
    home = Path.home()
    subprocess.run(['chezmoi', 'apply', '--include=files,dirs,symlinks',
                    str(home / '.local/share/icons' / theme),
                    str(home / '.config/gtk-4.0/settings.ini'),
                    str(home / '.config/dconf/interface.conf')], check=True)
    subprocess.run(['gtk-update-icon-cache', '--force', str(home / '.local/share/icons' / theme)], check=True)
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', theme], check=True)
    if subprocess.run(['systemctl', '--user', '--quiet', 'is-active', 'hamr-gtk.service']).returncode == 0:
        subprocess.run(['systemctl', '--user', 'restart', 'hamr-gtk.service'], check=True)
    print(f'Version {args.version.upper()} selected: {theme}. Preference saved in dotfiles.')


if __name__ == '__main__':
    main()
