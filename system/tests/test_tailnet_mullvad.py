"""Test native deployment and host scope without changing live networking."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('TJIKUP_BINARY', str(Path.home() / 'code/tjikos/apps/tjikup/target/debug/tjikup'))


class TailnetMullvadTests(unittest.TestCase):
    def test_client_native_policy_and_synthetic_deployment(self):
        for host in ('fi', 'li', 'si'):
            manifest = json.loads((ROOT / 'native' / host / 'manifest.json').read_text())
            entries = [e for e in manifest['entries'] if e.get('group') == 'tailnet-mullvad']
            self.assertEqual(len(entries), 2 if host in ('fi', 'li') else 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = json.loads((ROOT / 'native/fi/manifest.json').read_text())
            manifest['entries'] = [e for e in manifest['entries'] if e.get('group') == 'tailnet-mullvad']
            for entry in manifest['entries']:
                entry['uid'], entry['gid'] = os.getuid(), os.getgid()
                source = root / entry['source']
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes((ROOT / 'native/fi' / entry['source']).read_bytes())
            (root / 'manifest.json').write_text(json.dumps(manifest))
            target = root / 'target'
            target.mkdir()
            args = ['--manifest', str(root / 'manifest.json'), '--state-dir', str(root / 'state'), '--root', str(target)]
            for action in ('apply', 'check'):
                result = subprocess.run([BINARY, 'files', action, *args], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            unit = (target / 'etc/systemd/system/tailnet-mullvad.service').read_text()
            rules = (target / 'etc/tailnet-mullvad.nft').read_text()
            self.assertIn('WantedBy=multi-user.target', unit)
            self.assertIn('priority 5180 to 100.64.0.0/10 lookup 52', unit)
            self.assertIn('priority 5180 to fd7a:115c:a1e0::/48 lookup 52', unit)
            self.assertIn('priority -1', rules)
            self.assertIn('meta mark 0x6d6f6c65 ct mark set 0x00000f41 counter', rules)
            self.assertIn('rule del priority 5200', unit)
            self.assertIn('oifname "tailscale0" ip daddr 100.64.0.0/10', rules)
            self.assertNotIn('flush ruleset', rules)
            self.assertNotIn('destroy table inet mullvad', rules)
