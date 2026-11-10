"""Exercise the real Cargo credential manifests with synthetic BWS values only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("TJIKUP_BINARY", "/home/io/code/tjikos/apps/tjikup/target/debug/tjikup")
SECRET_ID = "00000000-0000-4000-8000-000000000123"


class CargoCredentialTests(unittest.TestCase):
    def fixture(self, root, host, enrolled=True):
        policy = root / "policy"
        policy.mkdir()
        shutil.copytree(ROOT / "native/home/templates", policy / "templates")
        spec = json.loads((ROOT / f"native/home/{host}.json").read_text())
        spec.pop("host", None)
        spec["context"].update({"user": {"name": "fixture", "home": "/fixture/home"},
                                "subscriptions": ["home:secrets"]})
        if host == "device":
            spec["context"]["is_client"] = True
        if enrolled:
            spec["context"]["cargo_registry_secret_id"] = SECRET_ID
        else:
            spec["context"].pop("cargo_registry_secret_id", None)
        marker = root / "must-not-execute"
        value = f"synthetic'quote\\slash $(touch {marker}) `false` $HOME\nsecond line"
        mock = root / "bws"
        mock.write_text(f"#!{sys.executable}\nimport json,sys\n"
                        f"assert sys.argv[1:4]==['secret','get',{SECRET_ID!r}]\n"
                        f"print(json.dumps({{'id':{SECRET_ID!r},'value':{value!r}}}))\n")
        mock.chmod(0o700)
        token = root / "access"
        token.write_text("BWS_ACCESS_TOKEN=synthetic\n")
        token.chmod(0o600)
        spec["bitwarden"] = {"command": [str(mock)], "access_token_file": str(token)}
        manifest = policy / "manifest.json"
        manifest.write_text(json.dumps(spec))
        destination = root / "destination"
        destination.mkdir()
        command = [BINARY, "files", "apply", "--manifest", str(manifest),
                   "--state-dir", str(root / "state"), "--root", str(destination),
                   "--group", "cargo-registry"]
        env = {**os.environ, "BWS_ACCESS_TOKEN": "synthetic", "XDG_CACHE_HOME": str(root / "cache"),
               "XDG_STATE_HOME": str(root / "state-home")}
        output = destination / "fixture/home/.cargo/credentials.toml"
        return command, env, output, value, marker

    def test_hosts_private_mode_quoting_idempotence_and_local_edits(self):
        for host in ("fi", "li", "si", "device"):
            with self.subTest(host=host), tempfile.TemporaryDirectory(prefix="cargo-policy-") as directory:
                command, env, output, value, marker = self.fixture(Path(directory), host)
                for attempt in range(2):
                    result = subprocess.run(command, capture_output=True, text=True, env=env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn(value, result.stdout + result.stderr)
                    if attempt:
                        self.assertIn("SKIP: 0 changed,", result.stdout)
                self.assertEqual(output.exists(), host != "si")
                if host != "si":
                    self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(tomllib.loads(output.read_text())["registry"]["token"], value)
                    changed = output.read_text() + '\n[registries.private]\ntoken = "local-token"\n'
                    output.write_text(changed)
                    result = subprocess.run(command, capture_output=True, text=True, env=env)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(output.read_text(), changed)
                self.assertFalse(marker.exists())

    def test_unenrolled_clients_do_not_render_a_placeholder(self):
        with tempfile.TemporaryDirectory(prefix="cargo-policy-") as directory:
            command, env, output, _, _ = self.fixture(Path(directory), "fi", enrolled=False)
            result = subprocess.run(command, capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(output.exists())

    def test_unmanaged_other_registry_credentials_are_preserved(self):
        with tempfile.TemporaryDirectory(prefix="cargo-policy-") as directory:
            command, env, output, _, _ = self.fixture(Path(directory), "li")
            output.parent.mkdir(parents=True)
            original = '[registries.private]\ntoken = "existing-local-token"\n'
            output.write_text(original)
            output.chmod(0o600)
            result = subprocess.run(command, capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output.read_text(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
