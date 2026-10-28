#!/usr/bin/env python3
"""Install current stable releases of the unmanaged client CLI tools."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

from github_api import github_json

SPECS = {
    "hyprvoice": ("LeonardoTrapani/hyprvoice", r"v(?P<version>\d+\.\d+\.\d+)",
                  "hyprvoice-linux-x86_64", "raw"),
    "tennis": ("gurgeous/tennis", r"v(?P<version>\d+\.\d+\.\d+)",
               "tennis_{version}_linux_amd64.tar.gz", "tar.gz"),
    "tinty": ("tinted-theming/tinty", r"v(?P<version>\d+\.\d+\.\d+)",
              "tinty-x86_64-unknown-linux-musl.tar.gz", "tar.gz"),
}


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def strata_release_metadata():
    """Resolve Strata metadata; its Fish installer retains the complete bundle."""
    release = github_json("https://api.github.com/repos/lgse/strata/releases/latest")
    match = re.fullmatch(r"v?(\d+\.\d+\.\d+)", release.get("tag_name", ""))
    if not match or release.get("draft") or release.get("prerelease"):
        raise RuntimeError("Latest Strata release has an unsupported version tag or is not stable")
    version = match.group(1)
    archive = f"strata-{version}-x86_64-unknown-linux-gnu.tar.gz"
    asset = next((item for item in release.get("assets", []) if item.get("name") == archive), None)
    if asset is None:
        raise RuntimeError(f"Latest Strata release is missing {archive}")
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise RuntimeError(f"Latest Strata release has no valid SHA-256 digest for {archive}")
    return version + "|" + digest.removeprefix("sha256:").lower()


def resolve_release(repo, tag_pattern, asset_pattern):
    releases = github_json(f"https://api.github.com/repos/{repo}/releases?per_page=100")
    tag_re = re.compile(tag_pattern)
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        match = tag_re.fullmatch(release.get("tag_name", ""))
        if not match:
            continue
        version = match.group("version")
        expected_name = asset_pattern.format(version=version)
        asset = next((item for item in release.get("assets", [])
                      if item.get("name") == expected_name), None)
        if asset is None:
            raise RuntimeError(f"Latest stable release {release['tag_name']} is missing {expected_name}")
        digest = asset.get("digest") or ""
        if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise RuntimeError(f"Release {release['tag_name']} has no SHA-256 digest for {expected_name}")
        return version, release["tag_name"], asset["browser_download_url"], digest.split(":", 1)[1].lower()
    raise RuntimeError(f"No stable release with the expected asset was found for {repo}")


def version_tuple(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        return None
    return tuple(map(int, match.groups()))


def safe_extract(archive, destination, kind):
    if kind == "tar.gz":
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(destination, filter="data")
        return
    if kind == "zip":
        root = destination.resolve()
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                path = (destination / member.filename).resolve()
                if path != root and root not in path.parents:
                    raise RuntimeError(f"Unsafe path in release archive: {member.filename}")
            bundle.extractall(destination)


def current_install(tool, link):
    if not link.is_symlink():
        if link.exists():
            raise RuntimeError(f"Refusing to overwrite unmanaged executable: {link}")
        return None, None
    target = link.resolve()
    if target.parent.parent != Path("/opt") / tool:
        return None, None
    version = target.parent.name.removeprefix("v")
    return version, target


def activate(tool, target):
    link = Path("/usr/local/bin") / tool
    if link.exists() and not link.is_symlink():
        raise RuntimeError(f"Refusing to overwrite unmanaged executable: {link}")
    if link.is_symlink() and link.resolve() == Path(target).resolve():
        return False
    temporary = link.with_name(link.name + ".chezetc-new")
    run("sudo", "-n", "install", "-d", "-m", "755", str(link.parent))
    run("sudo", "-n", "ln", "-sfn", str(target), str(temporary))
    run("sudo", "-n", "mv", "-Tf", str(temporary), str(link))
    return True


def install(tool, repo, tag_pattern, asset_pattern, archive_kind):
    version, tag, url, digest = resolve_release(repo, tag_pattern, asset_pattern)
    current_version, current_target = current_install(tool, Path("/usr/local/bin") / tool)
    current_tuple = version_tuple(current_version or "")
    release_tuple = version_tuple(version)
    if release_tuple is None:
        raise RuntimeError(f"Unsupported release version: {version}")

    changed = False
    if current_tuple and current_tuple > release_tuple:
        target = current_target
        print(f"{tool} {current_version}: keeping installed version newer than {version}")
    else:
        install_dir = (current_target.parent if current_version == version else Path("/opt") / tool / version)
        target = install_dir / tool
        marker = install_dir / ".installed"
        installed_digest = marker.read_text().strip() if marker.is_file() else ""
        if not target.is_file() or not os.access(target, os.X_OK) or installed_digest != digest:
            with tempfile.TemporaryDirectory(prefix=f"chezetc-{tool}-") as tmp_name:
                tmp = Path(tmp_name)
                download = tmp / "release"
                request = urllib.request.Request(url, headers={"User-Agent": "chezetc-client-updater"})
                with urllib.request.urlopen(request, timeout=60) as response, download.open("wb") as output:
                    shutil.copyfileobj(response, output)
                if hashlib.sha256(download.read_bytes()).hexdigest() != digest:
                    raise RuntimeError(f"SHA-256 mismatch for {tool} {version}")
                candidate = download
                if archive_kind != "raw":
                    extracted = tmp / "extract"
                    extracted.mkdir()
                    safe_extract(download, extracted, archive_kind)
                    candidates = [path for path in extracted.rglob(tool) if path.is_file()]
                    if len(candidates) != 1:
                        raise RuntimeError(f"Expected one {tool} binary in {tag}, found {len(candidates)}")
                    candidate = candidates[0]
                candidate.chmod(candidate.stat().st_mode | 0o111)
                env = os.environ.copy()
                if tool == "bw":
                    env["BITWARDENCLI_APPDATA_DIR"] = str(tmp / "check")
                check_args = [str(candidate), "--help"] if tool == "hyprvoice" else [str(candidate), "--version"]
                subprocess.run(check_args, check=True, stdout=subprocess.DEVNULL, env=env)
                install_dir = Path("/opt") / tool / version
                run("sudo", "-n", "install", "-d", "-m", "755", str(install_dir))
                run("sudo", "-n", "install", "-m", "755", str(candidate), str(target) + ".new")
                run("sudo", "-n", "mv", "-f", str(target) + ".new", str(target))
                marker_tmp = tmp / ".installed"
                marker_tmp.write_text(digest + "\n")
                run("sudo", "-n", "install", "-m", "644", str(marker_tmp), str(marker))
            changed = True
        changed = activate(tool, target) or changed
        print(f"{tool} {version}: installed or already current")

    if tool == "hyprvoice":
        local_bin = Path.home() / ".local/bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        user_link = local_bin / tool
        if user_link.exists() and not user_link.is_symlink():
            backup_dir = Path.home() / ".local/state/chezetc/hyprvoice"
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(user_link, backup_dir / f"hyprvoice-{__import__('time').time_ns()}")
        if not (user_link.is_symlink() and user_link.resolve() == (Path("/usr/local/bin") / tool).resolve()):
            user_link.unlink(missing_ok=True)
            user_link.symlink_to(Path("/usr/local/bin") / tool)
            changed = True
        subprocess.run([str(user_link), "--help"], check=True, stdout=subprocess.DEVNULL)
    return changed


def main():
    if os.uname().machine != "x86_64":
        raise RuntimeError("These client CLI releases currently support x86_64 only")
    selected = sys.argv[1:]
    if selected == ["strata-metadata"]:
        print(strata_release_metadata())
        return
    if selected == ["hyprvoice"]:
        changed = install("hyprvoice", *SPECS["hyprvoice"])
    elif selected == ["terminal"]:
        changed = False
        for tool in ("tennis", "tinty"):
            changed = install(tool, *SPECS[tool]) or changed
    else:
        raise RuntimeError("Expected tool selector: hyprvoice, terminal or strata-metadata")
    print("CHEZETC_RESULT=changed" if changed else "CHEZETC_RESULT=unchanged")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        sys.exit(str(error))
