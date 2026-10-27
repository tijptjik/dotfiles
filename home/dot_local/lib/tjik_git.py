"""Git-only synchronization policy for Dotjik, Systjik and Tooltjik."""
import argparse
from contextlib import ExitStack
import fcntl
import os
from pathlib import Path
import shlex
import subprocess
import sys


class SyncError(Exception):
    pass


def git(repo, *args, capture=True, env=None):
    result = subprocess.run(['git', '-C', str(repo), *args], text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, env=env)
    if result.returncode:
        raise SyncError(f'{repo}: git {shlex.join(args)} failed'
                        + (f'\n{result.stderr.strip()}' if capture else ''))
    return result.stdout.strip() if capture else None


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
        development = home / 'code/tooltjik'
        tool = development if (development / '.git').exists() else home / '.local/share/tooltjik'
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


def synchronize(repos, *, sync=False, dry_run=False):
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
                note = ' (will continue rebase with its existing commit message)'
            else:
                note = ' (uncommitted changes are not pushed)' if changes else ''
            print(f'{name}: {repo}{note}', flush=True)
        if not dry_run:
            for _, repo in repos:
                continue_rebase(repo)
            for _, repo in repos:
                preflight(repo, sync)
        # Pull all repos before pushing any. Never force-push or commit new work.
        operations = [('pull', '--rebase', '--no-autostash')] if sync else []
        operations += [('push',)]
        for operation in operations:
            for name, repo in repos:
                print(f'{name}: git {shlex.join(operation)}', flush=True)
                if not dry_run:
                    preflight(repo, sync)
                    git(repo, *operation, capture=False)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['push', 'sync'])
    parser.add_argument('--dry-run', action='store_true', help='check repositories and show commands without network or changes')
    args = parser.parse_args()
    try:
        return synchronize(repositories(), sync=args.action == 'sync', dry_run=args.dry_run)
    except (SyncError, OSError) as error:
        print(f'tjix: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
