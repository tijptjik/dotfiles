"""Interactive, reviewed synchronization using tjikup's presenter and Gum."""

import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import tjikup
from .core import ArchiveError, merge_entries, scan
from .feedback import Feedback


def visible(value):
    """Do not let file contents or names send control sequences to the terminal."""
    return ''.join(c if c in '\n\t' or (c.isprintable() and c != '\x7f') else f'\\x{ord(c):02x}' for c in str(value))


class Terminal:
    def __init__(self):
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ArchiveError('Guided sync needs a terminal; use sync for plan-only output')
        self.gum = shutil.which('gum')
        if not self.gum:
            raise ArchiveError('Guided sync requires gum (also used by tjikup)')
        self.repo = Path.home() / '.local/share/chezmoi'

    def choose(self, title, options):
        result = subprocess.run([self.gum, 'choose', '--header', visible(title), '--', *options], text=True, stdout=subprocess.PIPE)
        if result.returncode:
            raise KeyboardInterrupt
        answer = result.stdout.rstrip('\n')
        if answer not in options:
            raise ArchiveError('No valid selection received')
        return answer

    def page(self, text):
        result = subprocess.run([self.gum, 'pager', '--soft-wrap'], input=visible(text), text=True)
        if result.returncode:
            raise KeyboardInterrupt

    def confirm(self, title):
        result = subprocess.run([self.gum, 'confirm', '--default=false', visible(title)])
        if result.returncode in (0, 1):
            return result.returncode == 0
        raise KeyboardInterrupt

    def row(self, verb, icon, subject, note=''):
        tjikup.status_msg(self.repo, verb, icon, visible(subject), visible(note))


def describe(entry):
    if entry is None:
        return 'absent (choosing this side deletes the path)'
    fields = [entry['type'], f"mode {entry.get('mode', 0):04o}"]
    for key in ('size', 'sha256', 'target'):
        if key in entry:
            fields.append(f'{key}={entry[key]}')
    return ', '.join(fields)


def preview(plan, changes, conflicts):
    lines = [f"{plan['source']} → {plan['machine']}: {plan['folder']}",
             f"Snapshot: {plan['ref']['snapshot']}",
             f"{len(changes)} changes · {len(conflicts)} unresolved conflicts",
             f"Folder mode after sync: {plan['root_mode']:04o}"]
    if plan['policy']['mode'] == 'master':
        lines.append('EXACT MIRROR: managed local contents will match the desktop, including deletions.')
    lines += ['', 'Planned changes (relative to this device):']
    lines += [f"{item['action'].upper():8} {item['path']}" for item in changes]
    lines += [f'CONFLICT {name}' for name in conflicts]
    if not changes and not conflicts:
        lines.append('No file changes. Applying still records the synchronization baseline.')
    return '\n'.join(lines) + '\n'


class Review:
    def __init__(self, app, plan, directory):
        self.app, self.plan, self.directory = app, plan, directory
        self.loaded = False

    def show(self, name):
        p = self.plan
        lines = [f"{p['folder']}/{name}", f"Local ({p['machine']}): {describe(p['local'].get(name))}",
                 f"Source ({p['source']}): {describe(p['incoming'].get(name))}",
                 f"Last sync: {describe(p['base'].get(name))}", '']
        entries = (p['local'].get(name), p['incoming'].get(name))
        if any(e is not None and (e['type'] != 'file' or e['size'] > 1024 * 1024) for e in entries):
            return '\n'.join(lines) + 'Compare the metadata above for directories, symlinks and large files.\n'
        if scan(self.app.home / p['folder'], p['policy']) != p['local']:
            raise ArchiveError('Local state changed during review; retry to generate a fresh plan')
        if not self.loaded:
            ref, manifest = self.app.fetch(p['folder'], p['source'], self.directory, p['ref']['snapshot'], tree=True)
            if ref != p['ref'] or manifest['entries'] != p['incoming']:
                raise ArchiveError('Source snapshot changed during review')
            self.loaded = True
        contents = []
        for root, entry in zip((self.app.home / p['folder'], self.directory / 'tree'), entries):
            if entry is None:
                contents.append('')
                continue
            data = (root / name).read_bytes()
            try:
                if b'\0' in data:
                    raise UnicodeError
                contents.append(data.decode('utf-8'))
            except UnicodeError:
                return '\n'.join(lines) + 'Binary file: compare sizes and hashes above.\n'
        diff = ''.join(difflib.unified_diff(contents[0].splitlines(True), contents[1].splitlines(True),
                       fromfile='local/' + name, tofile=p['source'] + '/' + name))
        return '\n'.join(lines) + (diff or 'Text is identical; compare metadata above.\n')


def review_folder(app, folder, source, snapshot, ui):
    ui.row('CHECK', '…', folder, 'building sync plan')
    path, plan = app.plan(folder, source, snapshot)
    resolutions = {}
    with tempfile.TemporaryDirectory(prefix='review-', dir=app.state) as tmp:
        review = Review(app, plan, Path(tmp))
        while True:
            _, changes, conflicts = merge_entries(plan['base'], plan['local'], plan['incoming'], plan['policy']['mode'] == 'master', resolutions)
            ui.page(preview(plan, changes, conflicts))
            options = ['Resolve conflicts' if conflicts else 'Apply reviewed changes', 'Inspect a file', 'Skip folder', 'Quit']
            action = ui.choose(folder, options)
            if action == 'Quit':
                raise KeyboardInterrupt
            if action == 'Skip folder':
                return False
            if action == 'Inspect a file':
                names = sorted({c['path'] for c in changes} | set(plan['conflicts']))
                if not names:
                    ui.row('SKIP', '-', folder, 'no differing files')
                    continue
                labels = [f'{i + 1}: {visible(name).replace(chr(10), "\\n").replace(chr(9), "\\t")}' for i, name in enumerate(names)]
                choice = ui.choose('Select a file to compare', ['Back', *labels])
                if choice != 'Back':
                    ui.page(review.show(names[labels.index(choice)]))
                continue
            if conflicts:
                for name in conflicts:
                    if name not in plan['conflicts']:
                        raise ArchiveError('Resolutions created a structural conflict; retry this folder')
                    ui.page(review.show(name))
                    choice = ui.choose(f'{folder}: {visible(name)}', ['Keep local', 'Use source', 'Skip folder', 'Quit'])
                    if choice == 'Quit':
                        raise KeyboardInterrupt
                    if choice == 'Skip folder':
                        return False
                    resolutions[name] = 'local' if choice == 'Keep local' else 'source'
                continue
            title = f"Apply {len(changes)} changes to {folder} and record its sync baseline?"
            if plan['policy']['mode'] == 'master':
                title = f"EXACT MIRROR from {source}: " + title
            if not ui.confirm(title):
                continue
            ui.row('SYNC', '…', folder, 'verifying and applying')
            app.apply(path, resolutions)
            ui.row('SYNC', '✓', folder, 'verified')
            return True


def setup(app, source, folders=None, snapshot=None, ui=None):
    ui = ui or Terminal()
    folders = folders or [f for f, p in app.config['folders'].items()
                          if p['mode'] in ('sync', 'master') and app.eligible(f)]
    # Reject bad selections before any folder can be applied.
    if source == app.machine:
        raise ArchiveError('Choose a different source machine')
    for folder in folders:
        p = app.policy(folder)
        if not app.eligible(folder) or p['mode'] not in ('sync', 'master'):
            raise ArchiveError(f'{folder} is not a sync folder on this device')
        if p['mode'] == 'master' and (source != app.master or app.machine == app.master):
            raise ArchiveError(f'{folder} can only mirror the desktop onto another device')
    ui.row('REVIEW', '→', f'{source} → {app.machine}', f'{len(folders)} folders; Esc/Ctrl-C cancels')
    applied, skipped = [], []
    for folder in folders:
        while True:
            try:
                if review_folder(app, folder, source, snapshot, ui):
                    applied.append(folder)
                else:
                    skipped.append(folder)
                    ui.row('SKIP', '-', folder, 'left unchanged')
                break
            except (ArchiveError, OSError, ValueError, subprocess.CalledProcessError) as error:
                ui.row('FAILED', '✗', folder, 'review could not complete')
                ui.page(str(error))
                choice = ui.choose(folder, ['Retry this folder', 'Skip folder', 'Quit'])
                if choice == 'Quit':
                    raise KeyboardInterrupt
                if choice == 'Skip folder':
                    skipped.append(folder)
                    break
    ui.row('COMPLETE', '✓', 'Guided sync', f'{len(applied)} applied · {len(skipped)} skipped')
    try:
        app.ready()
    except ArchiveError as error:
        ui.row('WAIT', '-', 'Backup', 'initial sync incomplete')
        ui.page(str(error))
        return
    if skipped:
        ui.row('SKIP', '-', 'Backup', 'finish skipped folders, then run backup')
        return
    if ui.confirm(f'Back up {app.machine} now? This backs up all folders assigned to this device.'):
        folders = [f for f in app.config['folders'] if app.eligible(f)]
        feedback = Feedback()
        feedback.header(app.machine, len(folders))
        previous_report = app.report
        app.report = feedback.event
        try:
            for index, folder in enumerate(folders, 1):
                with feedback.folder(folder, index, len(folders)):
                    app.backup(folder)
        finally:
            app.report = previous_report
