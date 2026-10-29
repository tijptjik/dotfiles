"""One Strata result must retain dependency changes and failures."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StrataStatus(unittest.TestCase):
    def test_combined_status(self):
        text = (ROOT / 'native/tasks/system/run_53-install-strata.fish.j2').read_text()
        wrapper = text.split('function install_strata_complete\n', 1)[1].split('\nstep_run_quiet', 1)[0]
        for dependencies, app, failure in [('unchanged', 'unchanged', False), ('changed', 'unchanged', False), ('unchanged', 'changed', False), ('unchanged', 'changed', True)]:
            with self.subTest(dependencies=dependencies, app=app, failure=failure):
                script = f'''function install_strata_dependencies
    echo TJIKUP_RESULT={dependencies}
    return {1 if failure else 0}
end
function install_strata
    echo APP_RAN
    echo TJIKUP_RESULT={app}
end
function install_strata_complete
{wrapper}
install_strata_complete
'''
                result = subprocess.run(['fish', '--no-config', '-c', script], capture_output=True, text=True)
                if failure:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('APP_RAN', result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    markers = [line for line in result.stdout.splitlines() if line.startswith('TJIKUP_RESULT=')]
                    self.assertEqual(markers[-1], 'TJIKUP_RESULT=' + ('changed' if 'changed' in (dependencies, app) else 'unchanged'))
