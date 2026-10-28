#!/usr/bin/env python3
"""Install current stable Gitfetch releases in versioned directories."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from github_api import github_json

GITFETCH_REPO = "Matars/gitfetch"


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def latest_release(repo):
    releases = github_json(f"https://api.github.com/repos/{repo}/releases?per_page=100")
    for release in releases:
        tag = release.get("tag_name", "")
        if release.get("draft") or release.get("prerelease") or not tag.startswith("v"):
            continue
        version = tag[1:]
        if len(version.split(".")) != 3 or not all(part.isdecimal() for part in version.split(".")):
            continue
        return version, tag, release
    raise RuntimeError(f"No stable semantic-version release found for {repo}")


def activate(name, target):
    link = Path("/usr/local/bin") / name
    if link.exists() and not link.is_symlink():
        raise RuntimeError(f"Refusing to replace unmanaged command: {link}")
    if link.is_symlink() and link.resolve() == Path(target).resolve():
        return False
    temporary = link.with_name(name + ".new")
    run("sudo", "-n", "ln", "-sfn", str(target), str(temporary))
    run("sudo", "-n", "mv", "-Tf", str(temporary), str(link))
    return True


def install_gitfetch():
    version, tag, _ = latest_release(GITFETCH_REPO)
    commit_data = github_json(f"https://api.github.com/repos/{GITFETCH_REPO}/commits/{tag}")
    revision = commit_data.get("sha", "")
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise RuntimeError(f"GitHub returned an invalid Gitfetch commit for {tag}")
    target = Path("/opt/gitfetch") / revision[:12]
    changed = False
    marker = target / ".installed"
    if not marker.is_file() or marker.read_text().strip() != revision:
        with tempfile.TemporaryDirectory(prefix="chezetc-gitfetch-") as directory:
            temp = Path(directory)
            source = temp / "source"
            run("git", "clone", "--quiet", "--depth", "1", "--branch", tag,
                f"https://github.com/{GITFETCH_REPO}.git", str(source))
            actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
            if actual != revision:
                raise RuntimeError(f"Gitfetch tag {tag} resolved to {actual}, expected {revision}")
            run("sudo", "-n", "install", "-d", "-m", "755", str(target.parent))
            if not (target / "bin/python").is_file():
                run("/usr/bin/python3", "-m", "venv", str(target))
            run(str(target / "bin/pip"), "install", "--upgrade", "--force-reinstall", str(source))
            run(str(target / "bin/gitfetch"), "--help", stdout=subprocess.DEVNULL)
            marker_file = temp / ".installed"
            marker_file.write_text(revision + "\n")
            run("sudo", "-n", "install", "-d", "-m", "755", str(target))
            run("sudo", "-n", "chown", "-R", "root:root", str(target))
            run("sudo", "-n", "install", "-m", "644", str(marker_file), str(marker))
        changed = True
    changed = activate("gitfetch", target / "bin/gitfetch") or changed
    print(f"Gitfetch {version} ({revision[:12]}): installed or already current")
    return changed


def main():
    if os.uname().machine != "x86_64":
        raise RuntimeError("Gitfetch releases are currently available for x86_64 only")
    Path("/usr/local/bin").mkdir(parents=True, exist_ok=True)
    changed = install_gitfetch()
    print("CHEZETC_RESULT=changed" if changed else "CHEZETC_RESULT=unchanged")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        sys.exit(str(error))
