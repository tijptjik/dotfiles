"""Render real credential manifests with synthetic BWS data only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get(
    "TJIKUP_BINARY", str(Path.home() / "code/tjikos/apps/tjikup/target/debug/tjikup")
)


class RuntjikAmoCredentialTests(unittest.TestCase):
    def test_host_scope_private_mode_escaping_and_idempotence(self):
        for host in ["fi", "li", "si"]:
            with self.subTest(host=host), tempfile.TemporaryDirectory(prefix="amo-policy-") as temp:
                root = Path(temp)
                policy = root / "policy"
                policy.mkdir()
                shutil.copytree(ROOT / "native/home/templates", policy / "templates")
                spec = json.loads((ROOT / f"native/home/{host}.json").read_text())
                spec.pop("host", None)
                spec["context"]["user"]["home"] = "/fixture/home"
                marker = root / "must-not-execute"
                value = f"synthetic'quote\\slash $(touch {marker}) `false` $HOME\nsecond line"
                mock = root / "bws"
                mock.write_text(
                    "#!/usr/bin/env python3\nimport json, sys\n"
                    + f"print(json.dumps({{'id':sys.argv[3], 'value':{value!r}}}))\n"
                )
                mock.chmod(0o700)
                token = root / "token"
                token.write_text("BWS_ACCESS_TOKEN=synthetic\n")
                token.chmod(0o600)
                spec["bitwarden"] = {"command": [str(mock)], "access_token_file": str(token)}
                manifest = policy / "manifest.json"
                manifest.write_text(json.dumps(spec))
                destination = root / "destination"
                destination.mkdir()
                command = [
                    BINARY, "files", "apply", "--manifest", str(manifest),
                    "--state-dir", str(root / "state"), "--root", str(destination),
                ]
                env = {**os.environ, "BWS_ACCESS_TOKEN": "synthetic", "HOME": str(root),
                       "XDG_CACHE_HOME": str(root / "cache"), "XDG_STATE_HOME": str(root / "state-home")}
                for attempt in range(2):
                    result = subprocess.run(command, capture_output=True, text=True, env=env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn(value, result.stdout + result.stderr)
                    if attempt:
                        self.assertIn("SKIP: 0 changed,", result.stdout)
                output = destination / "fixture/home/.config/runtjik/amo.env"
                self.assertEqual(output.exists(), host == "fi")
                if host == "fi":
                    entry = next(e for e in spec["entries"] if e["path"].endswith("/runtjik/amo.env"))
                    self.assertTrue(entry["sensitive"])
                    self.assertEqual(entry["group"], "runtjik-amo")
                    self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                    loaded = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-c",
                         '. "$1"; printf "%s\\0%s" "$WEB_EXT_API_KEY" "$WEB_EXT_API_SECRET"',
                         "amo-test", str(output)], capture_output=True, env=env,
                    )
                    self.assertEqual(loaded.returncode, 0, loaded.stderr)
                    self.assertEqual(loaded.stdout, (value + "\0" + value).encode())
                    self.assertFalse(marker.exists())
                    grouped = subprocess.run(command + ["--group", "runtjik-amo"],
                                             capture_output=True, text=True, env=env)
                    self.assertEqual(grouped.returncode, 0, grouped.stderr)
                    self.assertIn("SKIP: 0 changed,", grouped.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
