"""Git-only synchronization policy for Dotjik, Systjik and Tooltjik."""
import argparse
import codecs
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import ExitStack
import fcntl
import os
from pathlib import Path
import pty
import re
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time
import tty


class SyncError(Exception):
    pass


def git(repo, *args, capture=True, env=None, include_stderr=False):
    result = subprocess.run(['git', '-C', str(repo), *args], text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, env=env)
    if result.returncode:
        raise SyncError(f'{repo}: git {shlex.join(args)} failed'
                        + (f'\n{result.stdout.strip()}\n{result.stderr.strip()}' if capture else ''))
    if capture:
        return (result.stdout + ('\n' + result.stderr if include_stderr else '')).strip()
    return None


def repositories():
    home = Path.home()
    dot = os.environ.get('DOTJIK_REPO')
    if not dot:
        result = subprocess.run(['chezmoi', 'source-path'], text=True, capture_output=True)
        if result.returncode or not result.stdout.strip():
            raise SyncError('Cannot determine the Chezmoi source directory; set DOTJIK_REPO.')
        # .chezmoiroot can place the source directory below the Git root.
        dot = git(Path(result.stdout.strip()), 'rev-parse', '--show-toplevel')
    tool = os.environ.get('TOOLTJIK_REPO')
    if not tool:
        tool = home / 'code/tooltjik'
        legacy = home / '.local/share/tooltjik'
        if not (tool.exists() or tool.is_symlink()) and (legacy.exists() or legacy.is_symlink()):
            raise SyncError(f'Move {legacy} to {tool} before retrying (see docs/tjikup.md).')
    return [('Dotjik', Path(dot).expanduser().resolve()),
            ('Systjik', Path(os.environ.get('SYSTJIK_REPO', home / '.local/share/chezetc')).expanduser().resolve()),
            ('Tooltjik', Path(tool).expanduser().resolve())]


def git_path(repo, name):
    path = Path(git(repo, 'rev-parse', '--git-path', name))
    return path if path.is_absolute() else repo / path


def rebase_state(repo):
    for name in ('rebase-merge', 'rebase-apply'):
        path = git_path(repo, name)
        if path.exists():
            # git am shares rebase-apply but must not be continued as a rebase.
            if name == 'rebase-apply' and not (path / 'rebasing').exists():
                raise SyncError(f'{repo}: git am is in progress; finish it first')
            return path
    return None


def preflight(repo, sync, *, allow_rebase=False):
    if git(repo, 'rev-parse', '--show-toplevel') != str(repo):
        raise SyncError(f'{repo}: expected a repository root')
    rebase = rebase_state(repo)
    if git(repo, 'diff', '--name-only', '--diff-filter=U'):
        raise SyncError(f'{repo}: unresolved conflicts; resolve them and git add the resolutions before retrying')
    if rebase and not allow_rebase:
        raise SyncError(f'{repo}: rebase paused again; inspect it and rerun the shortcut when ready')
    markers = ['REVERT_HEAD', 'BISECT_LOG', 'index.lock']
    if not rebase:
        markers += ['MERGE_HEAD', 'CHERRY_PICK_HEAD', 'sequencer']
    for marker in markers:
        if git_path(repo, marker).exists():
            raise SyncError(f'{repo}: unfinished Git operation ({marker}); finish it first')
    if rebase:
        branch = (rebase / 'head-name').read_text().strip()
        if not branch.startswith('refs/heads/'):
            raise SyncError(f'{repo}: rebase has no named branch; finish it manually')
        if git(repo, 'diff', '--name-only'):
            raise SyncError(f'{repo}: unstaged changes during rebase; stage the intended resolutions before retrying')
    else:
        branch = git(repo, 'symbolic-ref', '--quiet', 'HEAD')
    git(repo, 'rev-parse', '--abbrev-ref', branch.removeprefix('refs/heads/') + '@{upstream}')
    changes = git(repo, 'status', '--porcelain')
    if sync and (git(repo, 'ls-files', '--others', '--exclude-standard') if rebase else changes):
        raise SyncError(f'{repo}: working tree is dirty; commit or stash changes before tjixx')
    return changes


def continue_rebase(repo):
    if rebase_state(repo):
        preflight(repo, False, allow_rebase=True)
        print(f'{repo}: git rebase --continue', flush=True)
        # Keep the existing commit message; never stage, skip, abort or amend.
        git(repo, 'rebase', '--continue', capture=False,
            env={**os.environ, 'GIT_EDITOR': 'true'})
        preflight(repo, False)


class GitProgress:
    """Compose repository rows from Gum's animation without competing TTY writers."""

    def __init__(self, repos, stage):
        self.repos = repos
        self.stage = stage
        self.states = ['RUNNING'] * len(repos)
        self.started = time.monotonic()
        self.frame = '⠿'
        self.process = None
        self.master = None
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.animated = (sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'
                         and os.environ.get('TJIKUP_NO_SPIN') != '1'
                         and shutil.which('gum') is not None)

    def __enter__(self):
        if self.animated:
            master, slave = pty.openpty()
            self.master = master
            try:
                tty.setraw(slave)
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
                # Gum supplies the animation for every active row. Only this
                # renderer writes to the real terminal; Gum's probes stay private.
                self.process = subprocess.Popen(
                    ['gum', 'spin', '--spinner', 'dot', '--title', '', '--', 'sleep', '86400'],
                    stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
                    env={**os.environ, 'TERM': 'xterm-256color'})
                os.set_blocking(master, False)
            except OSError:
                os.close(master)
                self.master = None
                self.animated = False
            finally:
                os.close(slave)
        if self.animated:
            print('\033[?25l' + '\n' * len(self.repos), end='', flush=True)
            self.draw()
        else:
            for name, _ in self.repos:
                print(f'{name}: {self.stage} RUNNING', flush=True)
        return self

    def draw(self):
        if not self.animated:
            return
        try:
            data = os.read(self.master, 65536)
        except (BlockingIOError, OSError):
            data = b''
        frames = re.findall('[\u2800-\u28ff]', self.decoder.decode(data))
        if frames:
            self.frame = frames[-1]
        width = max(1, shutil.get_terminal_size((80, 24)).columns - 1)
        rows = []
        for (name, _), state in zip(self.repos, self.states):
            icon = self.frame if state == 'RUNNING' else ('✓' if state == 'OK' else '✗')
            row = f'{icon} {name:<8} {self.stage:<4} {state:<7} {int(time.monotonic() - self.started)}s'
            rows.append('\r\033[2K' + row[:width] + '\n')
        print(f'\033[{len(rows)}A' + ''.join(rows), end='', flush=True)

    def complete(self, index, success):
        self.states[index] = 'OK' if success else 'FAILED'
        if not self.animated:
            print(f'{self.repos[index][0]}: {self.stage} {self.states[index]}', flush=True)

    def __exit__(self, *_):
        try:
            if self.process is not None:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait()
        finally:
            if self.master is not None:
                os.close(self.master)
            if self.animated:
                print('\033[?25h', end='', flush=True)


def parallel_operation(repos, operation, *, sync, verbose=False):
    # A late invalid checkout still blocks the whole stage before launching Git.
    for _, repo in repos:
        preflight(repo, sync)
    errors = []
    output = {}
    with GitProgress(repos, operation[0].upper()) as progress:
        with ThreadPoolExecutor(max_workers=len(repos)) as executor:
            pending = {executor.submit(git, repo, *operation, include_stderr=True): index
                       for index, (_, repo) in enumerate(repos)}
            while pending:
                completed, _ = wait(pending, timeout=.08, return_when=FIRST_COMPLETED)
                for future in completed:
                    index = pending.pop(future)
                    try:
                        output[index] = future.result()
                    except (SyncError, OSError) as error:
                        errors.append(str(error))
                        progress.complete(index, False)
                    else:
                        progress.complete(index, True)
                progress.draw()
    # Successful command output is optional; failures always retain diagnostics.
    # Wait for every peer before reporting failure or starting another stage.
    if verbose:
        for index, (name, _) in enumerate(repos):
            if output.get(index):
                print(f'{name}:\n{output[index]}', flush=True)
    if errors:
        raise SyncError('\n'.join(errors))


def synchronize(repos, *, sync=False, dry_run=False, verbose=False):
    if len({path for _, path in repos}) != len(repos):
        raise SyncError('Repository paths must be distinct')
    with ExitStack() as stack:
        # Match Tjikup lock ordering: whole home workflow, then individual repos.
        locks = [(repos[0][1], 'tjikup-workflow.lock')]
        locks += [(repo, 'tjikup-sync.lock') for _, repo in sorted(repos, key=lambda item: str(item[1]))]
        for repo, name in locks:
            directory = Path(git(repo, 'rev-parse', '--absolute-git-dir'))
            if not dry_run:
                lock = stack.enter_context((directory / name).open('a'))
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise SyncError(f'{repo}: another Tjikup/Git sync is running; retry after it finishes') from None
        # Check every checkout before the first network operation.
        for name, repo in repos:
            changes = preflight(repo, sync, allow_rebase=True)
            if rebase_state(repo):
                note = 'will continue rebase with its existing commit message'
            else:
                note = 'uncommitted changes are not pushed' if changes else ''
            if verbose or dry_run:
                print(f'{name}: {repo}' + (f' ({note})' if note else ''), flush=True)
            elif note:
                print(f'{name}: {note}', flush=True)
        if not dry_run:
            for _, repo in repos:
                continue_rebase(repo)
            for _, repo in repos:
                preflight(repo, sync)
        # Pull all repos before pushing any. Never force-push or commit new work.
        operations = [('pull', '--rebase', '--no-autostash')] if sync else []
        operations += [('push',)]
        for operation in operations:
            if dry_run:
                for name, _ in repos:
                    print(f'{name}: git {shlex.join(operation)} (parallel {operation[0].upper()} stage)', flush=True)
            else:
                parallel_operation(repos, operation, sync=sync, verbose=verbose)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['push', 'sync'])
    parser.add_argument('--dry-run', action='store_true', help='check repositories and show commands without network or changes')
    parser.add_argument('-v', '--verbose', action='store_true', help='show repository paths and successful Git output')
    args = parser.parse_args()
    try:
        return synchronize(repositories(), sync=args.action == 'sync', dry_run=args.dry_run,
                           verbose=args.verbose)
    except (SyncError, OSError) as error:
        print(f'tjix: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
