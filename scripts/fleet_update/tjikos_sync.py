"""Synchronize the fleet's application checkout and its committed changes."""
from contextlib import contextmanager, nullcontext
import fcntl
import os
from pathlib import Path
import subprocess

from .core import UpdateError
from tjikup import runtime


def checkout():
    selected = os.environ.get("TJIKOS_REPO")
    if selected:
        return Path(selected).expanduser().resolve()
    target = Path.home() / "code/tjikos"
    legacy = Path.home() / ".local/share/tjikos"
    if not (target.exists() or target.is_symlink()) and (legacy.exists() or legacy.is_symlink()):
        raise UpdateError(f"Move {legacy} to {target} before retrying (see docs/tjikup.md)")
    return target.resolve()


def git(repo, *args, check=True):
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=240,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise UpdateError(f"tjikOS: {error}") from error
    if check and result.returncode:
        raise UpdateError(f"tjikOS: git {' '.join(args)} failed: "
                          + (result.stderr or result.stdout).strip())
    return result


@contextmanager
def locked_checkout(*, dry_run=False):
    repo = checkout()
    if not (repo / ".git").exists():
        if repo.exists():
            raise UpdateError(f"tjikOS: not a Git checkout: {repo}")
        runtime.stage_skip("tjikOS", "not cloned; installer will bootstrap")
        yield None
        return
    git_dir = Path(git(repo, "rev-parse", "--absolute-git-dir").stdout.strip())
    # Share the worktree lock used by tjix/tjixx, including linked worktrees.
    with (nullcontext() if dry_run else (git_dir / "tjikup-sync.lock").open("a")) as lock:
        if lock is not None:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise UpdateError("tjikOS checkout is busy; retry after its Git operation finishes") from None
        for marker in ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD",
                       "REVERT_HEAD", "BISECT_LOG", "index.lock"):
            if (git_dir / marker).exists():
                raise UpdateError(f"tjikOS has an unfinished Git operation ({marker}); finish it before updating")

        if git(repo, "status", "--porcelain", "--untracked-files=all").stdout:
            raise UpdateError("Dirty tjikOS: local changes; commit or stash before updating")
        yield repo


def warning(note):
    runtime.stage_label("WARN", "!", "tjikOS", note + "; using local checkout")
    return 0


def pull(*, dry_run=False):
    with locked_checkout(dry_run=dry_run) as repo:
        if repo is None:
            return 0
        branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
        if branch.returncode:
            return warning("detached HEAD; pull skipped")
        upstream = git(repo, "rev-parse", "--verify", "@{upstream}", check=False)
        if upstream.returncode:
            return warning("no upstream; pull skipped")
        remote = git(repo, "config", "--get", f"branch.{branch.stdout.strip()}.remote").stdout.strip()
        if dry_run:
            runtime.stage_label("CHECK", "✓", "tjikOS", "would fetch and fast-forward if behind")
            return 0

        git(repo, "fetch", "--no-recurse-submodules", "--", remote)
        # Fetch can take time. Recheck local work before moving the branch.
        if git(repo, "status", "--porcelain", "--untracked-files=all").stdout:
            raise UpdateError("Dirty tjikOS: local changes appeared; pull stopped")
        if git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).stdout != branch.stdout:
            return warning("branch changed; pull skipped")
        target = git(repo, "rev-parse", "@{upstream}").stdout.strip()
        ahead, behind = map(int, git(repo, "rev-list", "--left-right", "--count", f"HEAD...{target}").stdout.split())
        if ahead:
            if behind:
                return warning("diverged history; pull skipped")
            runtime.stage_skip("tjikOS", "↓0 · local commits; ready to push")
            return 0
        if not behind:
            runtime.stage_unchanged("tjikOS", "↓0; no changes")
            return 0
        git(repo, "merge", "--ff-only", "--no-autostash", target)
        runtime.stage_result("PULL", "tjikOS", f"↓{behind} · fast-forward")
    return 0


def push(*, dry_run=False):
    with locked_checkout(dry_run=dry_run) as repo:
        if repo is None:
            return 0
        branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
        if branch.returncode:
            return warning("detached HEAD; push skipped")
        upstream = git(repo, "rev-parse", "--verify", "@{upstream}", check=False)
        if upstream.returncode:
            return warning("no upstream; push skipped")
        if dry_run:
            runtime.stage_label("CHECK", "✓", "tjikOS", "would push committed changes if ahead")
            return 0
        ahead, behind = map(int, git(repo, "rev-list", "--left-right", "--count",
                                    f"HEAD...{upstream.stdout.strip()}").stdout.split())
        if behind:
            raise UpdateError("tjikOS: upstream commits remain; synchronize the branch before pushing")
        if not ahead:
            runtime.stage_unchanged("tjikOS", "↑0; no changes")
            return 0
        git(repo, "push")
        runtime.stage_result("PUSH", "tjikOS", f"↑{ahead}")
    return 0
