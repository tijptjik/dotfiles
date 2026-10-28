"""Route a clicked local file URL to Herdr's read-only file viewer."""
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit


def open_file(url):
    uri = urlsplit(url)
    if uri.scheme != "file" or uri.netloc not in {"", "localhost"} or uri.query or uri.fragment:
        raise ValueError("expected a local file URL")
    value = unquote(uri.path, errors="strict")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("invalid control character in file path")
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise ValueError("local file does not exist")
    command = [os.environ.get("HERDR_BIN_PATH") or "herdr", "plugin", "pane", "open",
               "--plugin", "herdr-file-viewer", "--entrypoint", "file-viewer",
               "--placement", "overlay", "--focus", "--cwd", str(path.parent),
               "--env", f"HERDR_FILE_VIEWER_OPEN={path}"]
    if pane := os.environ.get("HERDR_PANE_ID"):
        command.extend(["--target-pane", pane])
    subprocess.run(command, check=True)


if __name__ == "__main__":
    try:
        open_file(os.environ.get("HERDR_PLUGIN_CLICKED_URL", ""))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Could not open local file link: {error}", file=sys.stderr)
        raise SystemExit(1)
