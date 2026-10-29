"""Activation checks must detect drift without changing user services."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ActivationChecks(unittest.TestCase):
    def run_check(self, app, scenario='ready', legacy=False):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            binaries = home / 'bin'
            binaries.mkdir()
            systemctl = binaries / 'systemctl'
            systemctl.write_text('''#!/bin/bash
case "$*" in
  *is-enabled*dunst.service|*is-enabled*waybar.service)
    [[ "$SCENARIO" != unmasked ]] && echo masked
    exit 1 ;;
  *is-enabled*) [[ "$SCENARIO" != disabled ]]; exit $? ;;
  *is-active*graphical-session.target) [[ "$SCENARIO" != headless ]]; exit $? ;;
  *is-active*dunst.service|*is-active*waybar.service) [[ "$SCENARIO" == legacy-active ]]; exit $? ;;
  *is-active*) [[ "$SCENARIO" != inactive ]]; exit $? ;;
  *show*) [[ "$SCENARIO" == reload ]] && echo yes; exit 0 ;;
  *) echo "mutation attempted" >&2; exit 99 ;;
esac
''')
            systemctl.chmod(0o755)
            pgrep = binaries / 'pgrep'
            pgrep.write_text('#!/bin/bash\n[[ "$SCENARIO" == legacy-process ]]\n')
            pgrep.chmod(0o755)
            if legacy:
                (home / '.config').mkdir()
                (home / '.config' / ('dunst' if app == 'notjik' else 'waybar')).symlink_to(home / 'missing')
            result = subprocess.run(
                ['bash', str(ROOT / 'scripts' / f'activate-{app}.sh'), '--check'],
                env={**os.environ, 'HOME': str(home), 'PATH': f'{binaries}:{os.environ["PATH"]}', 'SCENARIO': scenario},
                capture_output=True, text=True,
            )
            self.assertNotIn('mutation attempted', result.stderr)
            return result.returncode

    def test_ready_and_headless(self):
        for app in ('notjik', 'bartjik'):
            for scenario in ('ready', 'headless'):
                with self.subTest(app=app, scenario=scenario):
                    self.assertEqual(self.run_check(app, scenario), 0)

    def test_missing_state_and_migration(self):
        for app in ('notjik', 'bartjik'):
            for scenario in ('disabled', 'unmasked', 'inactive', 'legacy-active', 'reload'):
                with self.subTest(app=app, scenario=scenario):
                    self.assertEqual(self.run_check(app, scenario), 1)
            self.assertEqual(self.run_check(app, legacy=True), 1)
        self.assertEqual(self.run_check('bartjik', 'legacy-process'), 1)


if __name__ == '__main__':
    unittest.main()
