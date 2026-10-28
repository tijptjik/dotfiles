"""Install the latest stable Tippecanoe release without modifying user sources."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from github_api import github_json

TOOLS = ("tippecanoe", "tippecanoe-enumerate", "tippecanoe-decode", "tile-join",
         "tippecanoe-json-tool", "tippecanoe-overzoom")


def release_tag(data):
    tag = data.get("tag_name", "")
    if data.get("draft") or data.get("prerelease") or not re.fullmatch(r"v?\d+\.\d+\.\d+", tag):
        raise RuntimeError("Upstream did not return a stable release tag")
    return tag


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def current_install(prefix):
    return (prefix / "revision").is_file() and all(
        (prefix / "bin" / name).is_file() and os.access(prefix / "bin" / name, os.X_OK)
        for name in TOOLS
    )


def activate(prefix, bin_dir=Path("/usr/local/bin")):
    for name in TOOLS:
        link = bin_dir / name
        if link.exists() and not link.is_symlink():
            raise RuntimeError(f"Refusing to overwrite unmanaged executable: {link}")
    run("sudo", "-n", "install", "-d", "-m", "755", str(bin_dir))
    for name in TOOLS:
        link = bin_dir / name
        target = prefix / "bin" / name
        if link.is_symlink() and link.resolve() == target:
            continue
        if link.exists() and not link.is_symlink():
            raise RuntimeError(f"Refusing to overwrite unmanaged executable: {link}")
        temporary = str(link) + ".chezetc-new"
        run("sudo", "-n", "ln", "-sfn", str(target), temporary)
        run("sudo", "-n", "mv", "-Tf", temporary, str(link))


def main():
    tag = release_tag(github_json("https://api.github.com/repos/felt/tippecanoe/releases/latest"))
    prefix = Path("/opt/tippecanoe") / tag
    if current_install(prefix):
        run(str(prefix / "bin/tippecanoe"), "--version")
        activate(prefix)
        print(f"Tippecanoe {tag}: already current")
        print("CHEZETC_RESULT=unchanged")
        return
    packages = ("git", "make", "gcc-c++", "sqlite-devel", "zlib-devel")
    missing = [p for p in packages if subprocess.run(
        ["rpm", "-q", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode]
    if missing:
        run("sudo", "-n", "dnf", "install", "-y", *missing)
    with tempfile.TemporaryDirectory(prefix="chezetc-tippecanoe-") as tmp:
        source = Path(tmp) / "source"
        run("git", "clone", "--depth", "1", "--branch", tag,
            "https://github.com/felt/tippecanoe.git", str(source))
        run("make", f"-j{min(os.cpu_count() or 1, 4)}", cwd=source)
        run(str(source / "unit"), cwd=source)
        run(str(source / "tippecanoe"), "--version")
        # Prove the executable can generate a real tile archive before activation.
        fixture = Path(tmp) / "point.geojson"
        fixture.write_text(json.dumps({"type": "Feature", "properties": {"name": "check"},
            "geometry": {"type": "Point", "coordinates": [114.1, 22.3]}}))
        run(str(source / "tippecanoe"), "-z", "0", "-o", str(Path(tmp) / "check.mbtiles"), str(fixture))
        stage = Path(tmp) / "install"
        run("make", "install", f"PREFIX={stage}", cwd=source)
        revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True)
        (stage / "revision").write_text(revision)
        run("sudo", "-n", "install", "-d", "-m", "755", str(prefix))
        run("sudo", "-n", "cp", "-a", str(stage) + "/.", str(prefix))
        run("sudo", "-n", "chown", "-R", "root:root", str(prefix))
        run(str(prefix / "bin/tippecanoe"), "--version")
        activate(prefix)
        print(f"Installed Tippecanoe {tag} ({revision.strip()})")
    print("CHEZETC_RESULT=changed")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        sys.exit(str(error))
