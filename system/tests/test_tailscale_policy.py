import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
import native_render
"""Client apply resumes enrolled tailnets without enrolling or disconnecting."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TailscalePolicyTests(unittest.TestCase):
    def test_rendered_client_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for host in ('fi', 'li', 'si'):
                config = root / 'config.json'
                config.write_text(json.dumps({'data': {
                    'isDesktop': host == 'fi', 'isLaptop': host == 'li',
                    'isClient': host != 'si', 'isServer': host == 'si',
                }}))
                rendered = subprocess.run([
                    'render-native', '--source', str(ROOT / 'etc'), '--config', str(config),
                    '--persistent-state', str(root / 'state.db'), 'execute-template',
                    '-f', str(ROOT / '../native/tasks/system/run_70-enable-tailscaled.fish.j2'),
                ], capture_output=True, text=True)
                self.assertEqual(rendered.returncode, 0, rendered.stderr)
                self.assertNotIn('tailscale down', rendered.stdout)
                syntax = subprocess.run(['fish', '--no-config', '--no-execute'],
                                        input=rendered.stdout, text=True, capture_output=True)
                self.assertEqual(syntax.returncode, 0, syntax.stderr)
                if host == 'si':
                    self.assertNotIn('tailscale set --accept-dns=false', rendered.stdout)
                    continue
                policy = rendered.stdout[rendered.stdout.index('# Keep ordinary DNS'):]
                harness = '''
set -l tailscale_prefs '{"CorpDNS":true,"RouteAll":true}'
function sudo; $argv; end
function systemctl
    echo "systemctl "(string join ' ' -- $argv) >> "$TRACE"
end
function timeout; set -e argv[1]; $argv; end
function step_skip_ok; end
function step_warn; echo warning; end
function step_fail; echo failure; end
function step_run_note; $argv[3..]; end
function tailscale
    echo (string join ' ' -- $argv) >> "$TRACE"
    switch $argv[1]
        case status; printf '{"BackendState":"%s"}\\n' "$TEST_STATE"
        case up; return $UP_STATUS
        case set; return 0
        case '*'; return 99
    end
end
'''
                for state, up_status, expected in [('Running', '0', 0), ('Stopped', '0', 0),
                                                   ('Stopped', '7', 1), ('NeedsLogin', '0', 0),
                                                   ('NeedsMachineAuth', '0', 0), ('Unavailable', '0', 1)]:
                    with self.subTest(host=host, state=state, up_status=up_status):
                        trace = root / 'trace'
                        trace.write_text('')
                        result = subprocess.run(['fish', '--no-config', '-c', harness + policy],
                            env={**os.environ, 'TEST_STATE': state, 'UP_STATUS': up_status, 'TRACE': str(trace)},
                            capture_output=True, text=True)
                        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
                        calls = trace.read_text().splitlines()
                        self.assertIn('set --accept-dns=false --accept-routes=false', calls)
                        self.assertEqual('up' in calls, state == 'Stopped')
                        self.assertNotIn('down', calls)
                        self.assertEqual('systemctl enable --now tailnet-dns.service' in calls,
                                         expected == 0)

    def test_current_preferences_issue_no_setters_and_drift_is_repaired(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'config.json'
            config.write_text(json.dumps({'data': {'isClient': True}}))
            rendered = subprocess.check_output([
                'render-native', '--source', str(ROOT / 'etc'), '--config', str(config),
                '--persistent-state', str(root / 'state.db'), 'execute-template',
                '-f', str(ROOT / '../native/tasks/system/run_70-enable-tailscaled.fish.j2'),
            ], text=True)
            policy = rendered.split('step_header "Tailscale"', 1)[1]
            tail = root / 'tailscale'
            tail.write_text(f'#!{sys.executable}\n' + r'''import os,sys
args=sys.argv[1:]
with open(os.environ['TRACE'],'a') as stream: stream.write(' '.join(args)+'\n')
if args==['debug','prefs']: print(os.environ['TEST_PREFS'])
elif args==['status','--json']: print('{"BackendState":"Running"}')
''')
            tail.chmod(0o755)
            harness = '''
function sudo; $argv; end
function systemctl; return 0; end
function step_skip_ok; printf 'SKIP %s\\n' $argv[1]; end
function step_fail; printf 'FAILED %s\\n' $argv[1]; end
function step_warn; printf 'WARN %s\\n' $argv[1]; end
function step_run_note; $argv[3..]; end
'''
            current = {'AutoUpdate': {'Apply': True}, 'OperatorUser': 'fixture',
                       'CorpDNS': False, 'RouteAll': False}
            for prefs, expected in [(current, []),
                    ({**current, 'CorpDNS': True}, ['set --accept-dns=false --accept-routes=false']),
                    ({**current, 'AutoUpdate': {'Apply': False}}, ['set --auto-update']),
                    ({**current, 'OperatorUser': 'other'}, ['set --operator=fixture'])]:
                with self.subTest(prefs=prefs):
                    trace = root / 'trace'
                    trace.write_text('')
                    result = subprocess.run(['fish', '--no-config', '-c', harness + policy],
                        env={**os.environ, 'PATH': str(root) + ':' + os.environ['PATH'],
                             'TRACE': str(trace), 'SUDO_USER': 'fixture',
                             'TEST_PREFS': json.dumps(prefs)}, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    calls = trace.read_text().splitlines()
                    self.assertEqual([call for call in calls if call.startswith('set ')], expected)
                    self.assertEqual(calls.count('debug prefs'), 1)
                    self.assertNotIn('up', calls)
                    self.assertNotIn('down', calls)
