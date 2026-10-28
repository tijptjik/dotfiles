#!/usr/bin/env python3
"""Ensure Bitwarden CLIs are installed; refresh releases only with --upgrade."""
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

from github_api import github_json

SPECS = {
    "bws": ("bitwarden/sdk-sm", r"bws-v(?P<version>\d+\.\d+\.\d+)",
            "bws-x86_64-unknown-linux-gnu-{version}.zip"),
    "bw": ("bitwarden/clients", r"cli-v(?P<version>\d{4}\.\d+\.\d+)",
           "bw-linux-{version}.zip"),
}


class ReleaseLookupError(RuntimeError):
    """Release metadata could not be fetched; installed tools may still work."""


class InstallResult(Enum):
    CURRENT = "current"
    UPDATED = "updated"
    DEFERRED = "deferred"


def run(*args):
    subprocess.run(args, check=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def public_metadata(url, *, redirect=False):
    """Public version requests carry no GitHub credentials and no binary body."""
    request = urllib.request.Request(url, method="HEAD" if redirect else "GET",
                                     headers={"User-Agent": "tjikup-bitwarden-updater",
                                              "Accept": "application/json"})
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            if redirect:
                raise RuntimeError("Bitwarden CLI download endpoint did not identify a release")
            return json.load(response)
    except urllib.error.HTTPError as error:
        if redirect and error.code in (301, 302, 303, 307, 308):
            return error.headers.get("Location", "")
        raise ReleaseLookupError(f"Product version lookup failed (HTTP {error.code})") from None
    except (urllib.error.URLError, TimeoutError):
        raise ReleaseLookupError("Product version lookup failed; check the network connection") from None
    except (ValueError, UnicodeError):
        raise ReleaseLookupError("Product version endpoint returned invalid JSON") from None


def latest_tag(tool):
    if tool == "bw":
        # Official Linux CLI link documented at https://bitwarden.com/help/cli/.
        # HEAD reads its release-specific redirect without downloading the ZIP.
        location = public_metadata("https://bitwarden.com/download/?app=cli&platform=linux",
                                   redirect=True)
        match = re.fullmatch(
            r"https://github\.com/bitwarden/clients/releases/download/cli-v"
            r"(?P<version>\d{4}\.\d+\.\d+)/bw-linux-(?P=version)\.zip", location)
        if not match:
            raise RuntimeError("Bitwarden CLI download endpoint returned an unexpected release URL")
        return "cli-v" + match.group("version")
    # sdk-sm publishes multiple products: /releases/latest can be the Python
    # SDK. The bws package's stable version identifies the CLI specifically.
    document = public_metadata("https://crates.io/api/v1/crates/bws")
    crate = document.get("crate", {}) if isinstance(document, dict) else {}
    if not isinstance(crate, dict) or crate.get("name") != "bws" or str(crate.get("repository", "")).removesuffix(".git") != "https://github.com/bitwarden/sdk-sm":
        raise RuntimeError("Unexpected bws package identity in version metadata")
    version = crate.get("max_stable_version", "")
    if not isinstance(version, str) or version_tuple(version) is None:
        raise RuntimeError("bws metadata has no valid stable CLI version")
    return "bws-v" + version


def latest_asset(tool):
    repo, tag_pattern, asset_pattern = SPECS[tool]
    tag = latest_tag(tool)
    match = re.fullmatch(tag_pattern, tag)
    if not match:
        raise RuntimeError(f"Unexpected {tool} release tag")
    try:
        release = github_json(f"https://api.github.com/repos/{repo}/releases/tags/{tag}")
    except RuntimeError as error:
        raise ReleaseLookupError(str(error)) from None
    if not isinstance(release, dict) or release.get("tag_name") != tag or release.get("draft") or release.get("prerelease"):
        raise RuntimeError(f"Expected a published stable release for {tag}")
    version = match.group("version")
    name = asset_pattern.format(version=version)
    asset = next((item for item in release.get("assets", []) if item.get("name") == name), None)
    if asset is None:
        raise RuntimeError(f"Stable release {tag} is missing {name}")
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise RuntimeError(f"Release {tag} has no SHA-256 digest for {name}")
    return version, asset["browser_download_url"], digest.split(":", 1)[1].lower()


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


def recorded_install(tool):
    """Cheap local convergence check; no process launch, credentials or network."""
    version, target = current_install(tool)
    if version_tuple(version or "") is None or target is None:
        return False
    marker = target.parent / ".installed"
    if not target.is_file() or not os.access(target, os.X_OK) or not marker.is_file():
        return False
    try:
        return bool(re.fullmatch(r"[0-9a-fA-F]{64}", marker.read_text().strip()))
    except (OSError, UnicodeError):
        return False


def usable_install(tool):
    """Runtime health check used only when an explicit release lookup fails."""
    if not recorded_install(tool):
        return False
    version, target = current_install(tool)
    with tempfile.TemporaryDirectory(prefix=f"chezmoi-{tool}-check-") as directory:
        env = os.environ.copy()
        if tool == "bw":
            env["BITWARDENCLI_APPDATA_DIR"] = directory
        try:
            result = subprocess.run([str(target), "--version"], capture_output=True,
                                    text=True, timeout=10, env=env)
        except (OSError, subprocess.TimeoutExpired):
            return False
    expected = {version, f"{tool} {version}"}
    return result.returncode == 0 and result.stdout.strip() in expected


def install_tool(tool, release=None):
    """Apply one verified release; only metadata discovery runs concurrently."""
    try:
        if isinstance(release, ReleaseLookupError):
            raise release
        version, url, digest = latest_asset(tool) if release is None else release
    except ReleaseLookupError as error:
        if not usable_install(tool):
            raise
        print(f"{tool}: keeping managed install; release check deferred: {error}")
        return InstallResult.DEFERRED
    changed = False
    current_version, current_target = current_install(tool)
    latest_tuple = version_tuple(version)
    installed_tuple = version_tuple(current_version or "")
    if installed_tuple and installed_tuple > latest_tuple:
        target = current_target
        print(f"{tool} {current_version}: keeping installed version newer than {version}")
        return InstallResult.CURRENT

    install_dir = current_target.parent if current_version == version else Path("/opt") / tool / version
    target = install_dir / tool
    marker = install_dir / ".installed"
    installed_digest = marker.read_text().strip() if marker.is_file() else ""
    if not target.is_file() or not os.access(target, os.X_OK) or installed_digest != digest:
        changed = True
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
        changed = True
        temporary_link = link.with_name(link.name + ".chezmoi-new")
        run("sudo", "ln", "-sfn", str(target), str(temporary_link))
        run("sudo", "mv", "-Tf", str(temporary_link), str(link))
    print(f"{tool} {version}: {'updated' if changed else 'already current'}")
    return InstallResult.UPDATED if changed else InstallResult.CURRENT


def lookup_releases(tools=None):
    """Fetch independent public metadata together, never install in workers."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {tool: pool.submit(latest_asset, tool) for tool in (SPECS if tools is None else tools)}
        releases = {}
        for tool, future in futures.items():
            try:
                releases[tool] = future.result()
            except ReleaseLookupError as error:
                releases[tool] = error
        return releases


def main(*, status_exit_code=False, upgrade=False):
    if os.uname().machine != "x86_64":
        raise RuntimeError("Bitwarden CLI releases are currently available for x86_64 only")
    needed = list(SPECS) if upgrade else [tool for tool in SPECS if not recorded_install(tool)]
    if not needed:
        print("Bitwarden CLIs: already installed (use --upgrade to check releases)")
        return 10 if status_exit_code else 0
    releases = lookup_releases(needed)
    results = [install_tool(tool, release=releases[tool]) for tool in needed]
    if InstallResult.DEFERRED in results:
        return 78
    return 10 if status_exit_code and InstallResult.UPDATED not in results else 0


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--upgrade", action="store_true",
                            help="check upstream releases even for installed tools")
        parser.add_argument("--status-exit-code", action="store_true",
                            help="exit 10 when both tools are already current")
        args = parser.parse_args()
        sys.exit(main(status_exit_code=args.status_exit_code, upgrade=args.upgrade))
    except RuntimeError as error:
        sys.exit(str(error))
