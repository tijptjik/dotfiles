"""Exercise cross-layer concurrency, barriers and timing with no live mutations."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

import tjikup_support
from fleet_update.dag import Task, run
from fleet_update.fleet_apply import combine, plans
from fleet_update.hook_tasks import HookTasks, owns_terminal

ROOT = Path(__file__).resolve().parents[1]


class CombinedTests(unittest.TestCase):
    def test_home_and_system_ready_work_really_overlaps(self):
        overlap = threading.Barrier(2, timeout=3)
        seen = []
        def work(name):
            overlap.wait()
            seen.append(name)
        home = [Task('home:wrapper', lambda: None), Task('home:compile', lambda: work('home'))]
        system = [Task('system:download', lambda: work('system'), ('system:files',))]
        preparation = Task('system:files', lambda: None, ('home:wrapper',), exclusive=True)
        # Home work also waits for preparation in this synthetic case so its
        # barrier cannot prevent the exclusive preparation from taking place.
        home[1].needs = ('system:files',)
        results = run(combine(home, system, preparation), workers=2)
        self.assertCountEqual(seen, ['home', 'system'])
        self.assertTrue(all(result.state == 'done' for result in results.values()), results)

    def test_cross_layer_resource_lock_and_timing(self):
        lease = threading.Lock()
        def work():
            self.assertTrue(lease.acquire(blocking=False))
            time.sleep(0.025)
            lease.release()
        tasks = [Task('home', work, resources=('dnf',)), Task('system', work, resources=('dnf',)),
                 Task('dependent', lambda: None, ('system',))]
        results = run(tasks, workers=3)
        self.assertTrue(all(result.state == 'done' for result in results.values()), results)
        self.assertGreater(results['system'].resource_wait, 0.015)
        self.assertGreater(results['dependent'].dependency_wait, 0.03)
        for result in results.values():
            self.assertAlmostEqual(result.seconds, result.finished - result.started, places=5)

    def test_terminal_requirement_is_evaluated_after_prerequisites(self):
        caller = threading.get_ident()
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / 'ca.pem'
            item = {'terminal_when_missing': str(marker)}
            self.assertTrue(owns_terminal(item))
            results = run([Task('setup', lambda: marker.write_text('ready')),
                Task('configured', lambda: self.assertNotEqual(threading.get_ident(), caller), ('setup',),
                     exclusive=lambda: owns_terminal(item))])
            self.assertEqual(results['configured'].state, 'done', results)

    def test_network_final_and_reboot_wait_for_every_peer(self):
        seen = set()
        def record(name):
            seen.add(name)
        home = [Task('home:wrapper', lambda: record('wrapper')), Task('home:network', lambda: record('home'))]
        system = [Task('system:download', lambda: record('system'), ('system:files',)),
                  Task('system:tailscale', lambda: self.assertTrue({'home', 'system'} <= seen), ('system:download',)),
                  Task('system:release', lambda: self.assertTrue({'home', 'system'} <= seen), exclusive=True)]
        tasks = combine(home, system, Task('system:files', lambda: None, ('home:wrapper',), exclusive=True),
                        {'system:tailscale': 'network-final', 'system:release': 'final'})
        results = run(tasks)
        self.assertTrue(all(result.state == 'done' for result in results.values()), results)
        release = results['system:release']
        self.assertGreaterEqual(release.started, max(r.finished for n, r in results.items() if n != 'system:release'))

    def test_failure_blocks_final_release_and_timings_are_private(self):
        def fail():
            raise RuntimeError('sensitive command output')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hooks = HookTasks(root, root, {})
            tasks = [Task('failure', fail), Task('release', lambda: self.fail('must block'), ('failure',))]
            with contextlib.redirect_stdout(io.StringIO()):
                results = run(tasks, workers=1, event=hooks.event)
            report = hooks.save_timings(tasks)
            self.assertEqual(results['release'].state, 'blocked')
            self.assertEqual(report.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('sensitive command output', report.read_text())
            records = json.loads(report.read_text())['tasks']
            self.assertEqual([r['state'] for r in records], ['failed', 'blocked'])
            self.assertIsNone(records[1]['started'])

    def test_service_refresh_waits_for_installers_before_network_and_release(self):
        seen = set()
        def finish(name):
            seen.add(name)
        def refresh():
            self.assertTrue({'home-install', 'system-install'} <= seen)
            seen.add('refresh')
        home = [Task('home:wrapper', lambda: None),
                Task('home:install', lambda: finish('home-install')),
                Task('home:services', refresh)]
        system = [Task('system:install', lambda: finish('system-install'), ('system:files',)),
                  Task('system:network', lambda: self.assertIn('refresh', seen)),
                  Task('system:release', lambda: None)]
        tasks = combine(home, system, Task('system:files', lambda: None, ('home:wrapper',)),
                        {'home:services': 'updates-final', 'system:network': 'network-final',
                         'system:release': 'final'})
        results = run(tasks, workers=4)
        self.assertTrue(all(result.state == 'done' for result in results.values()), results)
        self.assertGreaterEqual(results['home:services'].started, results['system:install'].finished)
        self.assertGreaterEqual(results['system:network'].started, results['home:services'].finished)

    def test_home_only_refresh_depends_on_every_installer(self):
        home, _, _ = plans(ROOT, ROOT.parent / 'chezetc')
        graph = {item['id']: item.get('needs', []) for item in home}
        def ancestors(name):
            return {name}.union(*(ancestors(parent) for parent in graph[name]))
        self.assertEqual(ancestors('services'), set(graph))

    def test_real_manifests_have_a_valid_combined_graph(self):
        home, system, _ = plans(ROOT, ROOT.parent / 'chezetc')
        self.assertGreater(len(home), 15)
        self.assertGreater(len(system), 15)
