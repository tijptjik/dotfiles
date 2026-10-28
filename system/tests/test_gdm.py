"""Render the managed GDM policy for each supported host role."""
import configparser
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi is required for rendering")
class GdmTests(unittest.TestCase):
    def test_host_autologin_users(self):
        template = (ROOT / "etc/gdm/custom.conf.tmpl").read_text()
        for host, client, user in (("fi", True, "io"), ("li", True, "io"), ("si", False, "m")):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                config = Path(tmp) / "config.toml"
                config.write_text("[data]\nisClient = " + str(client).lower() + "\nisServer = " + str(not client).lower() + "\n")
                result = subprocess.run(["chezmoi", "--config", str(config), "--source", str(ROOT), "execute-template"], input=template, text=True, capture_output=True, check=True)
                parsed = configparser.ConfigParser()
                parsed.read_string(result.stdout)
                self.assertTrue(parsed.getboolean("daemon", "AutomaticLoginEnable"))
                self.assertEqual(parsed.get("daemon", "AutomaticLogin"), user)
