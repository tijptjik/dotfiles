"""Update the fleet's application dependency without publishing development work."""
from contextlib import nullcontext
import fcntl
import os
from pathlib import Path
import subprocess

from .core import UpdateError
from tjikup import runtime


def checkout():
    selected = os.environ.get("TOOLTJIK_REPO")
    if selected:
        return Path(selected).expanduser().resolve()
    target = Path.home() / "code/tooltjik"
    legacy = Path.home() / ".local/share/tooltjik"
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
        raise UpdateError(f"Tooltjik: {error}") from error
    if check and result.returncode:
        raise UpdateError(f"Tooltjik: git {' '.join(args)} failed: "
                          + (result.stderr or result.stdout).strip())
    return result


def pull(*, dry_run=False):
    repo = checkout()
    if not (repo / ".git").exists():
        if repo.exists():
            raise UpdateError(f"Tooltjik: not a Git checkout: {repo}")
        runtime.stage_skip("Tooltjik", "not cloned; installer will bootstrap")
        return 0
    git_dir = Path(git(repo, "rev-parse", "--absolute-git-dir").stdout.strip())
    # Share the worktree lock used by tjix/tjixx, including linked worktrees.
    with (nullcontext() if dry_run else (git_dir / "tjikup-sync.lock").open("a")) as lock:
        if lock is not None:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise UpdateError("Tooltjik checkout is busy; retry after its Git operation finishes") from None
        for marker in ("rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD",
                       "REVERT_HEAD", "BISECT_LOG", "index.lock"):
            if (git_dir / marker).exists():
                raise UpdateError(f"Tooltjik has an unfinished Git operation ({marker}); finish it before updating")

        def warning(note):
            runtime.stage_label("WARN", "!", "Tooltjik", note + "; using local checkout")
            return 0

        if git(repo, "status", "--porcelain", "--untracked-files=all").stdout:
            return warning("local changes; pull skipped")
        branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
        if branch.returncode:
            return warning("detached HEAD; pull skipped")
        upstream = git(repo, "rev-parse", "--verify", "@{upstream}", check=False)
        if upstream.returncode:
            return warning("no upstream; pull skipped")
        remote = git(repo, "config", "--get", f"branch.{branch.stdout.strip()}.remote").stdout.strip()
        if dry_run:
            runtime.stage_label("CHECK", "✓", "Tooltjik", "would fetch and fast-forward if behind")
            return 0

        git(repo, "fetch", "--no-recurse-submodules", "--", remote)
        # Fetch can take time. Recheck local work before moving the branch.
        if git(repo, "status", "--porcelain", "--untracked-files=all").stdout:
            return warning("local changes appeared; pull skipped")
        if git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False).stdout != branch.stdout:
            return warning("branch changed; pull skipped")
        target = git(repo, "rev-parse", "@{upstream}").stdout.strip()
        ahead, behind = map(int, git(repo, "rev-list", "--left-right", "--count", f"HEAD...{target}").stdout.split())
        if ahead:
            return warning("diverged history; pull skipped" if behind else "local commits; pull skipped")
        if not behind:
            runtime.stage_unchanged("Tooltjik")
            return 0
        git(repo, "merge", "--ff-only", "--no-autostash", target)
        runtime.stage_result("PULL", "Tooltjik", f"{behind} {'commit' if behind == 1 else 'commits'} · fast-forward")
    return 0
