"""Exercise Zapfast defaults without replacing existing account/security settings."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("TJIKUP_BINARY", "/home/io/code/tjikos/apps/tjikup/target/debug/tjikup")


class ZapfastConfigTests(unittest.TestCase):
    def test_client_defaults_and_existing_private_settings(self):
        entries = json.loads((ROOT / "native/home/files.json").read_text())
        entries = [entry for entry in entries if "/.config/zapfast" in entry["path"]]
        for host in ("fi", "li", "si"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(ROOT / "native/home/files/.config/zapfast", root / "files/.config/zapfast")
                manifest = root / "manifest.json"
                manifest.write_text(json.dumps({
                    "version": 1,
                    "id": "zapfast-fixture",
                    "context": {"user": {"home": "/fixture/home"}, "is_client": host != "si"},
                    "entries": entries,
                }))
                destination = root / "destination"
                destination.mkdir()
                command = [BINARY, "files", "apply", "--manifest", str(manifest),
                           "--state-dir", str(root / "state"), "--root", str(destination)]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = destination / "fixture/home/.config/zapfast"
                if host == "si":
                    self.assertFalse(config.exists())
                    continue
                settings = config / "settings.json"
                defaults = json.loads(settings.read_text())
                self.assertEqual(defaults["wallpaper_image"], "/fixture/home/.config/zapfast/wallpaper.png")
                self.assertEqual(settings.stat().st_mode & 0o777, 0o600)
                self.assertTrue((config / "wallpaper.png").is_file())
                self.assertTrue((config / "themes/Rose Punk.json").is_file())
                private_settings = '{"app_lock_hash":"synthetic-private-hash","giphy_key":"synthetic-key"}\n'
                settings.write_text(private_settings)
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(settings.read_text(), private_settings)
