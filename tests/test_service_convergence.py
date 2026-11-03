"""Exercise check/apply/skip and drift repair without live services or credentials."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

STUB = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
path = pathlib.Path(os.environ['FIXTURE_STATE'])
s = json.loads(path.read_text())
a = sys.argv[1:]
cmd = pathlib.Path(sys.argv[0]).name
if s.get('error') == cmd:
    sys.exit(7)
if s.get('invalid') == cmd:
    print('not JSON'); sys.exit(0)
def save():
    path.write_text(json.dumps(s))
def mutate():
    with open(os.environ['FIXTURE_TRACE'], 'a') as f:
        f.write(cmd + ' ' + ' '.join(a) + '\n')
    save()
if cmd == 'hostname':
    print(s.get('host', 'fi'))
elif cmd == 'systemctl':
    a = [v for v in a if v != '--user']
    unit = a[-1]
    prop = next((v.split('=', 1)[1] for v in a if v.startswith('--property=')), '')
    if a[0] == 'show':
        print(s.get(unit, {}).get(prop, {'UnitFileState':'disabled', 'ActiveState':'inactive', 'NeedDaemonReload':'no'}[prop]))
    elif a[0] == 'cat':
        print(s.get('unit_text', 'managed unit'))
    elif a[0] == 'daemon-reload':
        for value in s.values():
            if isinstance(value, dict): value['NeedDaemonReload'] = 'no'
        mutate()
    elif a[0] == 'enable':
        s.setdefault(unit, {})['UnitFileState'] = 'enabled'
        if '--now' in a: s[unit]['ActiveState'] = 'active'
        mutate()
    elif a[0] == 'restart':
        s.setdefault(unit, {})['ActiveState'] = 'active'
        if unit == 'tailnet-mullvad.service': s['routes'] = True; s['legacy'] = False
        if unit == 'tailnet-dns.service': s['dns'] = True; s[unit]['ActiveState'] = 'inactive'
        mutate()
    else: raise RuntimeError(a)
elif cmd == 'nft':
    if a[0] == '-f':
        s['policy'] = 'current'; mutate()
    elif a[-1] == 'tables':
        print(json.dumps({'nftables': [{'table': {'family':'inet', 'name':'tailnet_mullvad'}}] if s.get('policy') else []}))
    else:
        print(json.dumps({'nftables':[{'metainfo':{'version':'fixture'}}, {'rule':{'handle':s.get('handle', 1), 'expr':[{'policy':s.get('policy')}, {'counter':{'packets':s.get('packets', 0), 'bytes':42}}]}}]}))
elif cmd == 'ip':
    dst = '100.64.0.0/10' if '-4' in a else 'fd7a:115c:a1e0::/48'
    rules = [{'priority':5100, 'dst':dst, 'table':52}] if s.get('routes') else []
    if s.get('legacy'): rules.append({'priority':5197, 'dst':dst, 'table':52})
    print(json.dumps(rules))
elif cmd == 'resolvectl':
    values = {'dns':'100.85.220.100', 'domain':'~tailb49776.ts.net tjik.internal', 'default-route':'no'}
    print('Link 4 (tailscale0): ' + (values[a[0]] if s.get('dns') else 'wrong'))
else: raise RuntimeError(cmd)
'''


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for command in ('systemctl', 'hostname', 'nft', 'ip', 'resolvectl'):
            path = self.bin / command
            path.write_text(STUB)
            path.chmod(0o755)
        self.state = self.root / 'state.json'
        self.state.write_text('{}')
        self.trace = self.root / 'trace'
        self.trace.write_text('')
        self.env = {**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH'],
                    'FIXTURE_STATE': str(self.state), 'FIXTURE_TRACE': str(self.trace)}

    def change(self, **values):
        data = json.loads(self.state.read_text())
        data.update(values)
        self.state.write_text(json.dumps(data))

    def run_script(self, script, *args, expected=0):
        result = subprocess.run(['bash', str(script), *args], env=self.env,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result


class TailnetConvergence(Fixtures):
    def setUp(self):
        super().setUp()
        self.script = self.root / 'tailnet.sh'
        self.policy = self.root / 'policy.nft'
        self.policy.write_text('managed policy')
        self.script.write_text((ROOT / 'scripts/tailnet-services.sh').read_text()
            .replace('/var/lib/tjikup/tailnet-services', str(self.root / 'receipts'))
            .replace('/etc/tailnet-mullvad.nft', str(self.policy)))

    def converge(self, component):
        self.run_script(self.script, '--check', component, expected=1)
        self.run_script(self.script, '--apply', component)
        self.run_script(self.script, '--check', component)
        before = self.trace.read_text()
        self.run_script(self.script, '--apply', component)
        self.assertEqual(self.trace.read_text(), before)

    def test_second_run_skips_and_live_drift_is_repaired(self):
        for component in ('policy', 'routing', 'dns', 'timer'):
            with self.subTest(component=component):
                self.converge(component)
        self.change(packets=500, handle=999)
        self.run_script(self.script, '--check', 'policy')
        self.change(policy='wrong')
        self.converge('policy')
        self.policy.write_text('changed managed policy')
        self.converge('policy')
        for drift in ({'routes': False}, {'legacy': True}, {'unit_text': 'changed unit'},
                      {'tailnet-mullvad.service': {'UnitFileState':'enabled', 'ActiveState':'active', 'NeedDaemonReload':'yes'}}):
            self.change(**drift)
            self.converge('routing')
        self.change(dns=False)
        self.converge('dns')
        self.change(**{'tailnet-dns.timer': {'UnitFileState':'enabled', 'ActiveState':'inactive'}})
        self.converge('timer')

    def test_probe_errors_do_not_apply(self):
        for component in ('policy', 'routing', 'dns', 'timer'):
            self.converge(component)
        for command, component in [('nft', 'policy'), ('systemctl', 'routing'),
                                   ('ip', 'routing'), ('resolvectl', 'dns')]:
            self.change(error=command)
            before = self.trace.read_text()
            self.run_script(self.script, '--check', component, expected=2)
            self.run_script(self.script, '--apply', component, expected=2)
            self.assertEqual(self.trace.read_text(), before)
            self.change(error=None)
        for command, component in [('nft', 'policy'), ('ip', 'routing')]:
            self.change(invalid=command)
            before = self.trace.read_text()
            self.run_script(self.script, '--apply', component, expected=2)
            self.assertEqual(self.trace.read_text(), before)
            self.change(invalid=None)


class NotificationConvergence(Fixtures):
    def setUp(self):
        super().setUp()
        self.home = self.root / 'home'
        self.home.mkdir()
        self.repo = self.root / 'dotjik'
        (self.repo / 'scripts').mkdir(parents=True)
        for name in ('install-notjik-service.sh', 'ensure-tjikos.sh'):
            shutil.copy(ROOT / 'scripts' / name, self.repo / 'scripts' / name)
        self.script = self.repo / 'scripts/install-notjik-service.sh'
        self.tool = self.home / 'code/tjikos'
        (self.tool / '.git').mkdir(parents=True)
        app = self.tool / 'apps/notjik-service'
        (app / 'scripts').mkdir(parents=True)
        (app / 'systemd').mkdir()
        (app / 'systemd/notjik-sync.service').write_text('managed service\n')
        (self.tool / 'packages/notjik-sync/src').mkdir(parents=True)
        (self.tool / 'packages/notjik-sync/src/main.rs').write_text('original source')
        (app / 'scripts/build.sh').write_text('''#!/bin/bash
set -eu
echo build >> "$FIXTURE_TRACE"
cd "$(dirname "$0")/.."
mkdir -p dist/bin
printf '#!/bin/bash\\nexit 0\\n' > dist/bin/notjik-api
cat > dist/bin/notjik-sync <<'SYNC'
#!/bin/bash
mkdir -p "$HOME/.config/notjik"
echo '{}' > "$HOME/.config/notjik/sync.json"
SYNC
chmod +x dist/bin/*
''')
        self.env.update(HOME=str(self.home), TJIKOS_REPO=str(self.tool))

    def test_build_once_then_skip_and_repair_only_what_changed(self):
        self.run_script(self.script, '--check', expected=1)
        self.assertEqual(self.trace.read_text(), '')
        self.run_script(self.script)
        self.run_script(self.script, '--check')
        before = self.trace.read_text()
        self.run_script(self.script)
        self.assertEqual(self.trace.read_text(), before)
        self.assertEqual(before.count('build\n'), 1)
        self.change(**{'notjik-sync.service': {'UnitFileState':'enabled', 'ActiveState':'inactive'}})
        self.run_script(self.script, '--check', expected=1)
        self.run_script(self.script)
        self.assertEqual(self.trace.read_text().count('build\n'), 1)
        self.run_script(self.script, '--check')
        binary = self.home / '.local/bin/notjik-sync'
        binary.write_text('damaged')
        self.run_script(self.script, '--check', expected=1)
        self.run_script(self.script)
        self.assertEqual(self.trace.read_text().count('build\n'), 2)
        (self.tool / 'packages/notjik-sync/src/main.rs').write_text('new source')
        self.run_script(self.script, '--check', expected=1)
        self.run_script(self.script)
        self.assertEqual(self.trace.read_text().count('build\n'), 3)
        self.run_script(self.script, '--check')
        self.change(error='systemctl')
        before = self.trace.read_text()
        self.run_script(self.script, '--check', expected=2)
        self.run_script(self.script, '--apply', expected=2)
        self.assertEqual(self.trace.read_text(), before)


class NotificationAuthorityCheck(Fixtures):
    def setUp(self):
        super().setUp()
        self.change(host='si')
        sudo = self.bin / 'sudo'
        sudo.write_text('#!/bin/bash\n[[ "$1" != -n ]] || shift\nexec "$@"\n')
        sudo.chmod(0o755)
        self.home = self.root / 'home'
        self.system = self.root / 'system'
        self.script = self.root / 'activate.sh'
        self.script.write_text((ROOT / 'scripts/activate-notjik-api.sh').read_text()
            .replace('/usr/local/', str(self.system) + '/usr/local/')
            .replace('/etc/notjik/', str(self.system) + '/etc/notjik/'))
        runner = self.bin / 'runner'
        runner.write_text('#!/bin/bash\nexit 0\n')
        runner.chmod(0o755)
        self.env.update(HOME=str(self.home), TJIKUP_BINARY=str(runner))
        self.paths = [self.home / '.local/lib/notjik-service/notjik-api',
                      self.home / '.local/bin/notjik-sync',
                      self.system / 'usr/local/lib/notjik/notjik-api',
                      self.system / 'usr/local/bin/notjik-sync']

    def test_missing_and_stopped_authority_need_apply_but_probe_errors_fail(self):
        self.run_script(self.script, '--check', expected=1)
        for path in self.paths[:2]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture binary')
            path.chmod(0o755)
        # A missing installed server binary is drift, not cmp's exit 2/error.
        self.run_script(self.script, '--check', expected=1)
        for path in self.paths[2:]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture binary')
            path.chmod(0o755)
        config = self.system / 'etc/notjik/system-client.json'
        config.parent.mkdir(parents=True)
        config.write_text('{}')
        self.run_script(self.script, '--check', expected=1)
        for unit in ('notjik-api.service', 'notjik-serve.service', 'notjik-system-sync.service'):
            self.change(**{unit: {'UnitFileState':'enabled', 'ActiveState':'active', 'NeedDaemonReload':'no'}})
        self.run_script(self.script, '--check')
        self.paths[-1].write_text('outdated binary')
        self.run_script(self.script, '--check', expected=1)
        self.paths[-1].write_text('fixture binary')
        self.change(error='systemctl')
        self.run_script(self.script, '--check', expected=2)
        self.assertEqual(self.trace.read_text(), '')
