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


def git(repo, *args, capture=True):
    result = subprocess.run(['git', '-C', str(repo), *args], text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
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


def preflight(repo, sync):
    if git(repo, 'rev-parse', '--show-toplevel') != str(repo):
        raise SyncError(f'{repo}: expected a repository root')
    git(repo, 'symbolic-ref', '--quiet', 'HEAD')
    git(repo, 'rev-parse', '--abbrev-ref', '@{upstream}')
    for marker in ('rebase-merge', 'rebase-apply', 'MERGE_HEAD', 'CHERRY_PICK_HEAD',
                   'REVERT_HEAD', 'sequencer', 'BISECT_LOG', 'index.lock'):
        path = Path(git(repo, 'rev-parse', '--git-path', marker))
        if not path.is_absolute():
            path = repo / path
        if path.exists():
            raise SyncError(f'{repo}: unfinished Git operation ({marker}); finish it first')
    changes = git(repo, 'status', '--porcelain')
    if sync and changes:
        raise SyncError(f'{repo}: working tree is dirty; commit or stash changes before tjixx')
    return changes


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
            changes = preflight(repo, sync)
            print(f'{name}: {repo}' + (' (uncommitted changes are not pushed)' if changes else ''), flush=True)
        # Pull all repos before pushing any. Never force-push or create commits.
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
