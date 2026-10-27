"""Exercise renamed greeting installation without touching live tools or dotfiles."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GreetjikInstallTests(unittest.TestCase):
    def test_build_install_and_cache_use_renamed_app(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = root / 'tools'
            (tools / '.git').mkdir(parents=True)
            build = tools / 'apps/greetjik/scripts/build.sh'
            build.parent.mkdir(parents=True)
            build.write_text('echo build >> "$CALL_LOG"\n')
            install = tools / 'scripts/install.sh'
            install.parent.mkdir()
            install.write_text('''
set -eu
test "$1" = greetjik
echo "install $1" >> "$CALL_LOG"
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/licenses/greetjik"
printf 'renderer' > "$HOME/.local/bin/greetjik"
printf 'license' > "$HOME/.local/share/licenses/greetjik/LICENSE"
''')
            scripts = root / 'scripts'
            scripts.mkdir()
            for name in ('install-greetjik.sh', 'ensure-tjikos.sh', 'cache-install.py'):
                shutil.copy2(ROOT / 'scripts' / name, scripts / name)
            log = root / 'calls'
            env = {**os.environ, 'HOME': str(root / 'home'),
                   'TJIKOS_REPO': str(tools), 'CALL_LOG': str(log),
                   'XDG_STATE_HOME': str(root / 'state')}
            def run_install():
                return subprocess.run(['bash', str(scripts / 'install-greetjik.sh')],
                                      env=env, capture_output=True, text=True)
            first = run_install()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(log.read_text().splitlines(), ['build', 'install greetjik'])
            second = run_install()
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn('SKIP', second.stdout)
            self.assertEqual(log.read_text().splitlines(), ['build', 'install greetjik'])
            # A missing renamed binary must trigger installation again.
            (root / 'home/.local/bin/greetjik').unlink()
            repaired = run_install()
            self.assertEqual(repaired.returncode, 0, repaired.stderr)
            self.assertEqual(log.read_text().splitlines(),
                             ['build', 'install greetjik', 'build', 'install greetjik'])


if __name__ == '__main__':
    unittest.main()
