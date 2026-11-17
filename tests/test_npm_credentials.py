"""Registry credentials use synthetic secrets and isolated fixture homes only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get('TJIKUP_BINARY', '/home/io/code/tjikos/apps/tjikup/target/debug/tjikup')
IDS = ['00000000-0000-4000-8000-000000000121', '00000000-0000-4000-8000-000000000122']


class NpmCredentialsTests(unittest.TestCase):
    def test_hosts_enrollment_permissions_and_existing_files(self):
        for host in ['fi', 'li', 'si', 'device']:
            for enrolled in [True, False, "npm-only"]:
                with self.subTest(host=host, enrolled=enrolled), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    shutil.copytree(ROOT / 'native/home/templates', root / 'templates')
                    spec = json.loads((ROOT / f'native/home/{host}.json').read_text())
                    spec.pop('host', None)
                    spec['context'].update({'user': {'name': 'fixture', 'home': '/fixture/home'}, 'subscriptions': ['home:secrets']})
                    if host == 'device':
                        spec['context']['is_client'] = True
                    for key in ['npm_publish_secret_id', 'github_packages_secret_id']:
                        spec['context'].pop(key, None)
                    if enrolled:
                        spec['context']['npm_publish_secret_id'] = IDS[0]
                        if enrolled != 'npm-only':
                            spec['context']['github_packages_secret_id'] = IDS[1]
                    mock = root / 'bws'
                    mock.write_text(f'#!{sys.executable}\nimport json,sys\nvalues={dict(zip(IDS, ["npm_synthetic", "ghp_synthetic"]))!r}\nprint(json.dumps({{"id":sys.argv[3],"value":values[sys.argv[3]]}}))\n')
                    mock.chmod(0o700)
                    token = root / 'access'
                    token.write_text('BWS_ACCESS_TOKEN=synthetic\n')
                    token.chmod(0o600)
                    spec['bitwarden'] = {'command': [str(mock)], 'access_token_file': str(token)}
                    manifest = root / 'manifest.json'
                    manifest.write_text(json.dumps(spec))
                    destination = root / 'destination'
                    destination.mkdir()
                    output = destination / 'fixture/home/.npmrc'
                    command = [BINARY, 'files', 'apply', '--manifest', str(manifest), '--state-dir', str(root / 'state'), '--root', str(destination), '--group', 'npm-registry']
                    env = {**os.environ, 'BWS_ACCESS_TOKEN': 'synthetic', 'XDG_CACHE_HOME': str(root / 'cache'), 'XDG_STATE_HOME': str(root / 'state-home')}
                    for _ in range(2):
                        result = subprocess.run(command, env=env, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertNotIn('npm_synthetic', result.stdout + result.stderr)
                        self.assertNotIn('ghp_synthetic', result.stdout + result.stderr)
                    self.assertEqual(output.exists(), bool(enrolled) and host != 'si')
                    if output.exists():
                        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                        content = output.read_text()
                        self.assertIn('//registry.npmjs.org/:_authToken=npm_synthetic', content)
                        if enrolled == 'npm-only':
                            self.assertNotIn('npm.pkg.github.com', content)
                        else:
                            self.assertIn('//npm.pkg.github.com/:_authToken=ghp_synthetic', content)
                        self.assertNotIn('@saanseoi:registry', content)
                        changed = content + '\n# local edit\n'
                        output.write_text(changed)
                        result = subprocess.run(command, env=env, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(output.read_text(), changed)


if __name__ == '__main__':
    unittest.main()
