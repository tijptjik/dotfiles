#!/usr/bin/env python3
"""Install theme metadata and retire overrides without changing the selected theme."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def with_ini_setting(text, section, key, value):
    """Update one setting without reformatting the rest of a GTK/Qt config."""
    lines = text.splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        if line.strip().startswith('['):
            if inside:
                lines.insert(i, f'{key}={value}\n')
                return ''.join(lines)
            inside = line.strip() == f'[{section}]'
        elif inside and line.partition('=')[0].strip() == key:
            lines[i] = f'{key}={value}\n'
            return ''.join(lines)
    if inside:
        return ''.join(lines).rstrip('\n') + f'\n{key}={value}\n'
    return text.rstrip('\n') + ('\n\n' if text else '') + f'[{section}]\n{key}={value}\n'


def select_theme(config, theme, graphical):
    changed = False
    for relative, section, key in (
        ('gtk-3.0/settings.ini', 'Settings', 'gtk-icon-theme-name'),
        ('gtk-4.0/settings.ini', 'Settings', 'gtk-icon-theme-name'),
        ('qt6ct/qt6ct.conf', 'Appearance', 'icon_theme'),
    ):
        path = config / relative
        before = path.read_text() if path.exists() else ''
        after = with_ini_setting(before, section, key, theme)
        if before != after:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(after)
            changed = True
    if graphical:
        current = subprocess.check_output(
            ['gsettings', 'get', 'org.gnome.desktop.interface', 'icon-theme'], text=True).strip().strip("'")
        if current != theme:
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', theme], check=True)
            changed = True
    return changed


def migrate_legacy_theme(config, graphical):
    """Rename the selected Rose Punk ID without changing other theme choices."""
    changed = False
    for relative, section, key in (
        ('gtk-3.0/settings.ini', 'Settings', 'gtk-icon-theme-name'),
        ('gtk-4.0/settings.ini', 'Settings', 'gtk-icon-theme-name'),
        ('qt6ct/qt6ct.conf', 'Appearance', 'icon_theme'),
    ):
        path = config / relative
        if not path.is_file():
            continue
        before = path.read_text()
        settings = configparser.ConfigParser(interpolation=None, strict=False)
        settings.read_string(before)
        if settings.get(section, key, fallback='') == 'rose-punk-illustrated':
            path.write_text(with_ini_setting(before, section, key, 'rose-punk'))
            changed = True
    if graphical:
        current = subprocess.check_output(
            ['gsettings', 'get', 'org.gnome.desktop.interface', 'icon-theme'], text=True).strip().strip("'")
        if current == 'rose-punk-illustrated':
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', 'rose-punk'], check=True)
            changed = True
    return changed


def icon_fingerprint(folder):
    digest = hashlib.sha256()
    for path in sorted(folder.rglob('*')):
        if path.is_file() and (path.suffix == '.svg' or path.name == 'index.theme'):
            digest.update(str(path.relative_to(folder)).encode() + b'\0' + path.read_bytes())
    return digest.hexdigest()


def with_icon(text, icon):
    """Replace the main entry icon; preserve actions, comments and localized fields."""
    lines = text.splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        if line.strip().startswith('['):
            if inside:
                lines.insert(i, f'Icon={icon}\n')
                return ''.join(lines)
            inside = line.strip() == '[Desktop Entry]'
        elif inside and line.startswith('Icon='):
            lines[i] = f'Icon={icon}\n'
            return ''.join(lines)
    if inside:
        return ''.join(lines).rstrip('\n') + f'\nIcon={icon}\n'
    raise ValueError('Missing Desktop Entry section')


def main_icon(text):
    inside = False
    for line in text.splitlines():
        if line.startswith('['):
            inside = line.strip() == '[Desktop Entry]'
        elif inside and line.startswith('Icon='):
            return line[5:].strip()
    return ''


def managed_icons(source):
    result = {}
    for path in source.glob('*'):
        if not path.is_file():
            continue
        icon = main_icon(path.read_text())
        if icon and not icon.startswith('rose-punk-') and '{{' not in icon:
            result[path.name.removeprefix('executable_').removesuffix('.tmpl').removesuffix('.j2')] = icon
    return result


def restore_overrides(data, state, managed, vendor_roots):
    """Retire only our icon overrides; retain edits to commands and other fields."""
    record_path = state / 'desktop-overrides.json'
    records = json.loads(record_path.read_text()) if record_path.exists() else {}
    backup_path = state / 'theme-switch-backups.json'
    backups = json.loads(backup_path.read_text()) if backup_path.exists() else {}
    applications = data / 'applications'
    count, issues = 0, []

    def replace(path, text, replacement):
        nonlocal count
        backups.setdefault(path.name, text)
        backup_path.write_text(json.dumps(backups, indent=2) + '\n')
        backup_path.chmod(0o600)
        if replacement is None:
            path.unlink()
        else:
            # A user launcher can itself be a symlink into a package directory.
            # Replace the local entry, never follow it when writing an override.
            with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(replacement)
            try:
                temporary.chmod(path.stat().st_mode & 0o777)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        count += 1

    for target in sorted(applications.glob('*.desktop')):
        text = target.read_text()
        icon = main_icon(text)
        record = records.get(target.name)
        # Managed launch commands are authoritative; change only their icon field.
        if icon.startswith('rose-punk-') and target.name in managed:
            replace(target, text, with_icon(text, managed[target.name]))
            records.pop(target.name, None)
            continue
        if record and text == record['installed']:
            replace(target, text, record['original'])
            records.pop(target.name)
            continue
        if not icon.startswith('rose-punk-'):
            records.pop(target.name, None)
            continue
        original = record.get('original') if record else None
        candidates = [original] if original else []
        for root in vendor_roots:
            path = root / target.name
            if path.is_file():
                candidates.append(path.read_text())
        replacement = next((main_icon(candidate) for candidate in candidates
                            if main_icon(candidate) and not main_icon(candidate).startswith('rose-punk-')), None)
        if replacement:
            replace(target, text, with_icon(text, replacement))
            records.pop(target.name, None)
        else:
            issues.append(target.name)
    # Preserve unresolved records for inspection/recovery, including absent files.
    record_path.write_text(json.dumps(records, indent=2) + '\n')
    record_path.chmod(0o600)
    return count, issues


def remove_theme_fallbacks(data):
    """Remove our symlinks, never vendor icon files or links to other themes."""
    themes = [(data / 'icons' / name).resolve() for name in ('rose-punk', 'rose-punk-illustrated', 'rose-punk-framed')]
    removed = 0
    for path in (data / 'icons/hicolor').rglob('*'):
        if path.is_symlink() and any(path.resolve().is_relative_to(theme) for theme in themes):
            path.unlink()
            removed += 1
    return removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true', help='compatibility alias: retire legacy overrides')
    parser.add_argument('--status-note', action='store_true', help='emit a compact note for the status presenter')
    args = parser.parse_args()
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME', home / '.local/share'))
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state')) / 'rose-punk-icons'
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    source = Path(__file__).resolve().parents[2] / 'native/home/files/.local/share/applications'
    vendors = [home / '.local/share/flatpak/exports/share/applications',
               Path('/usr/local/share/applications'), Path('/usr/share/applications'),
               Path('/var/lib/flatpak/exports/share/applications')]
    changed, issues = restore_overrides(data, state, managed_icons(source), vendors)
    removed = remove_theme_fallbacks(data)
    primary = configparser.ConfigParser(interpolation=None)
    primary.read(data / 'icons/rose-punk/index.theme')
    if (primary.get('Icon Theme', 'Name', fallback='') == 'Rose Punk'
            and not primary.getboolean('Icon Theme', 'Hidden', fallback=False)):
        config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
        migrated = migrate_legacy_theme(config, bool(os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY')))
    else:
        migrated = False
    for theme in ('rose-punk', 'rose-punk-illustrated', 'rose-punk-framed'):
        if (data / 'icons' / theme / 'index.theme').exists():
            refresh_cache(['gtk-update-icon-cache', '--force', str(data / 'icons' / theme)])
    if (data / 'icons/hicolor').exists():
        refresh_cache(['gtk-update-icon-cache', '--force', '--ignore-theme-index', str(data / 'icons/hicolor')])
    if (data / 'applications').exists():
        refresh_cache(['update-desktop-database', str(data / 'applications')])
    # Only a renamed Rose Punk ID is migrated; other theme choices stay intact.
    for name in issues:
        print(f'WARN    ! Icon override needs review: {name}')
    note = f'{changed} launcher overrides retired; {removed} fallback links removed' if changed or removed else 'no changes'
    if migrated:
        note = 'theme ID migrated' + (f'; {note}' if note != 'no changes' else '')
    print(f'__stage_note__:{note}' if args.status_note else f'Rose Punk setup: {note}')


def refresh_cache(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        print(result.stdout, end='')
        result.check_returncode()


if __name__ == '__main__':
    main()
