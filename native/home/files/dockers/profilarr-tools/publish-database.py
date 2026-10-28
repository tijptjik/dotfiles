#!/usr/bin/env python3
"""Publish the committed policy subtree as a PCD branch without changing checkout."""
import os
import pathlib
import subprocess

PREFIX = "home/dockers/profilarr-database"
BRANCH = "profilarr"

def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "Git operation failed")
    return result.stdout.strip()

repo = git("rev-parse", "--show-toplevel")
os.chdir(repo)
if not pathlib.Path(repo, PREFIX, "pcd.json").is_file():
    raise SystemExit("Run from the dotfiles source checkout")
if git("status", "--porcelain", "--", PREFIX):
    raise SystemExit("Commit the profile database changes before publishing")
source = git("rev-parse", "HEAD")
tree = git("rev-parse", f"{source}:{PREFIX}")
remote = git("ls-remote", "--heads", "origin", f"refs/heads/{BRANCH}")
parent = remote.split()[0] if remote else None
args = ["commit-tree", tree]
if parent:
    git("fetch", "origin", f"refs/heads/{BRANCH}")
    if git("rev-parse", f"{parent}^{{tree}}") == tree:
        print("Profilarr database branch already matches committed source")
        raise SystemExit(0)
    args += ["-p", parent]
commit = git(*args, "-m", f"Sync Profilarr database from dotfiles {source[:12]}")
git("push", "origin", f"{commit}:refs/heads/{BRANCH}")
print(f"Published Profilarr database {commit[:12]} from {source[:12]}")
