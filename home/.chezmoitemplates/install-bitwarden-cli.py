#!/usr/bin/env python3
"""Install the latest stable Bitwarden CLI releases with verified assets."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from github_api import github_json

SPECS = {
    "bws": ("bitwarden/sdk-sm", r"bws-v(?P<version>\d+\.\d+\.\d+)",
            "bws-x86_64-unknown-linux-gnu-{version}.zip"),
    "bw": ("bitwarden/clients", r"cli-v(?P<version>\d{4}\.\d+\.\d+)",
           "bw-linux-{version}.zip"),
}


def run(*args):
    subprocess.run(args, check=True)


def latest_asset(tool):
    repo, tag_pattern, asset_pattern = SPECS[tool]
    releases = github_json(f"https://api.github.com/repos/{repo}/releases?per_page=100")
    tag_re = re.compile(tag_pattern)
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        match = tag_re.fullmatch(release.get("tag_name", ""))
        if not match:
            continue
        version = match.group("version")
        name = asset_pattern.format(version=version)
        asset = next((item for item in release.get("assets", []) if item.get("name") == name), None)
        if asset is None:
            raise RuntimeError(f"Latest stable release {release['tag_name']} is missing {name}")
        digest = asset.get("digest") or ""
        if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise RuntimeError(f"Release {release['tag_name']} has no SHA-256 digest for {name}")
        return version, asset["browser_download_url"], digest.split(":", 1)[1].lower()
    raise RuntimeError(f"No stable {tool} release with the expected Linux asset was found")


def version_tuple(value):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    return tuple(map(int, match.groups())) if match else None


def current_install(tool):
    link = Path("/usr/local/bin") / tool
    if not link.is_symlink():
        if link.exists():
            raise RuntimeError(f"Refusing to overwrite unmanaged executable: {link}")
        return None, None
    target = link.resolve()
    if target.parent.parent != Path("/opt") / tool:
        return None, None
    return target.parent.name.removeprefix("v"), target


def install_tool(tool):
    version, url, digest = latest_asset(tool)
    current_version, current_target = current_install(tool)
    latest_tuple = version_tuple(version)
    installed_tuple = version_tuple(current_version or "")
    if installed_tuple and installed_tuple > latest_tuple:
        target = current_target
        print(f"{tool} {current_version}: keeping installed version newer than {version}")
        return

    install_dir = current_target.parent if current_version == version else Path("/opt") / tool / version
    target = install_dir / tool
    marker = install_dir / ".installed"
    installed_digest = marker.read_text().strip() if marker.is_file() else ""
    if not target.is_file() or not os.access(target, os.X_OK) or installed_digest != digest:
        with tempfile.TemporaryDirectory(prefix=f"chezmoi-{tool}-") as directory:
            temp = Path(directory)
            archive = temp / "release.zip"
            request = urllib.request.Request(url, headers={"User-Agent": "chezmoi-bitwarden-updater"})
            with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
            if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"SHA-256 mismatch for {tool} {version}")
            extracted = temp / "release"
            extracted.mkdir()
            root = extracted.resolve()
            with zipfile.ZipFile(archive) as bundle:
                for member in bundle.infolist():
                    path = (extracted / member.filename).resolve()
                    if path != root and root not in path.parents:
                        raise RuntimeError(f"Unsafe path in {tool} archive: {member.filename}")
                bundle.extractall(extracted)
            candidates = [path for path in extracted.rglob(tool) if path.is_file()]
            if len(candidates) != 1:
                raise RuntimeError(f"Expected one {tool} binary in {version}, found {len(candidates)}")
            binary = candidates[0]
            binary.chmod(binary.stat().st_mode | 0o111)
            env = os.environ.copy()
            if tool == "bw":
                env["BITWARDENCLI_APPDATA_DIR"] = str(temp / "check")
            subprocess.run([str(binary), "--version"], check=True, stdout=subprocess.DEVNULL, env=env)
            run("sudo", "install", "-d", "-m", "755", str(install_dir))
            run("sudo", "install", "-m", "755", str(binary), str(target) + ".new")
            run("sudo", "mv", "-f", str(target) + ".new", str(target))
            marker_tmp = temp / ".installed"
            marker_tmp.write_text(digest + "\n")
            run("sudo", "install", "-m", "644", str(marker_tmp), str(marker))

    link = Path("/usr/local/bin") / tool
    if link.exists() and not link.is_symlink():
        raise RuntimeError(f"Refusing to overwrite unmanaged executable: {link}")
    if not (link.is_symlink() and link.resolve() == target.resolve()):
        temporary_link = link.with_name(link.name + ".chezmoi-new")
        run("sudo", "ln", "-sfn", str(target), str(temporary_link))
        run("sudo", "mv", "-Tf", str(temporary_link), str(link))
    print(f"{tool} {version}: installed or already current")


def main():
    if os.uname().machine != "x86_64":
        raise RuntimeError("Bitwarden CLI releases are currently available for x86_64 only")
    for tool in ("bws", "bw"):
        install_tool(tool)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        sys.exit(str(error))
