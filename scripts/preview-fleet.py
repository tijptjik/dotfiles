#!/usr/bin/env python3
"""Render sample fleet rows for visual review without running update operations."""
import argparse
from pathlib import Path
import sys

# The installed runner is a zipapp, just as in the fleet entry point.
runner = Path.home() / '.local/bin/tjikup'
if runner.is_file():
    sys.path.insert(0, str(runner))
from tjikup_dependency import check_runtime

if not check_runtime():
    raise SystemExit(1)

from fleet_update.icons import HookProgress
from fleet_update.preparation import prepare
from fleet_update.status import NATIVE_LABELS
from fleet_update.repository_progress import RepositoryProgress
from tjikup import runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('section', nargs='?', choices=('setup', 'capture', 'repositories', 'all'), default='all')
    parser.add_argument('--dirty-files', type=int, help='Show a sample failed pull with this file count')
    parser.add_argument('--wait', action='store_true', help='Keep the sample visible until Enter')
    args = parser.parse_args()
    print('Tjikup display review · sample outcomes only', flush=True)
    progress = HookProgress(live=False)

    def rows(title, labels, verb):
        section = HookProgress(section=title, live=False)
        for label in labels:
            section.finish(label, label, verb=verb, record=False)

    if args.section in ('setup', 'all'):
        rows('Prerequisites', ['Bitwarden', 'Chezmoi', 'Fish', 'UV', 'Gum', 'Bun'], 'SKIP')
        runtime.section_header('Managed Dotfiles')
        progress.finish('bitwarden', 'Bitwarden (CLIs)', verb='UPDATE', note='1.24s', record=False)
        progress.finish('fonts', 'Assets (font folder migration)', verb='SKIP', note='no changes', record=False)
        def native_preparation():
            for subject, verb in [
                    ('Bitwarden access token', 'CONFIG'), ('chezmoi decryption key', 'CONFIG'),
                    ('System packages', 'SYNC'), ('Essential packages', 'INSTALL'),
                    ('Passwordless sudo', 'CONFIG'), ('Default shell', 'CONFIG'),
                    ('Symbolic link icon', 'CONFIG')]:
                progress.finish(subject, NATIVE_LABELS[subject], verb=verb, record=False)
            return 0
        prepare('Chezmoi (home directory)', 'APPLY', native_preparation)
        prepare('Chezetc (system)', 'CHECK', lambda: None)
        runtime.section_header('Home + System Tasks')
        progress.finish('gdm-session', 'GDM (Hyprland login)', verb='DONE', record=False)
    if args.section in ('capture', 'all'):
        rows('Commit Local Changes', ['Zed', 'Herdr', 'Solaar', 'Fcitx', 'Codex', 'Zapzap',
                                     'Gtk-bookmarks', 'Local Changes'], 'SKIP')
    if args.section in ('capture', 'repositories', 'all'):
        with RepositoryProgress(live=False) as repositories:
            repositories.open()
            for repo in repositories.repositories:
                repositories.update(repo, 'PULL', 'changed', count=3)
                repositories.update(repo, 'PUSH', 'unchanged', count=0)
            if args.dirty_files is not None:
                repositories.update('dotjik', 'PULL', 'failed', note=f'{args.dirty_files} files')
                for repo in repositories.repositories:
                    repositories.update(repo, 'PUSH', 'blocked')
            repositories.settle()
    if args.wait:
        print('\nDisplay review complete. Press Enter to close.', flush=True)
        sys.stdin.readline()


if __name__ == '__main__':
    main()
