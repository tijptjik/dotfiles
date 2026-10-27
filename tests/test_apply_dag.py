"""Dependencies, resource exclusion and safe skips using synthetic work only."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.dag import Task, run, validate

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('install_cache', ROOT / 'scripts/cache-install.py')
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


class DagTests(unittest.TestCase):
    def test_ready_tasks_overlap_and_dependents_wait(self):
        barrier = threading.Barrier(2, timeout=3)
        finished = set()
        def work(name):
            barrier.wait()
            finished.add(name)
        def dependent():
            self.assertEqual(finished, {'a', 'b'})
        results = run([Task('a', lambda: work('a')), Task('b', lambda: work('b')),
                       Task('c', dependent, needs=('a', 'b'))])
        self.assertTrue(all(r.state == 'done' for r in results.values()), results)

    def test_shared_resources_serialize_check_and_write(self):
        busy = threading.Lock()
        def check():
            self.assertTrue(busy.acquire(blocking=False))
            return False
        def write():
            self.assertTrue(busy.locked())
            busy.release()
        results = run([Task(str(n), write, resources=('cargo',), check=check) for n in range(8)])
        self.assertTrue(all(r.state == 'done' for r in results.values()), results)

    def test_skip_satisfies_dependencies(self):
        seen = []
        results = run([Task('a', lambda: self.fail('must skip'), check=lambda: True),
                       Task('b', lambda: seen.append('b'), needs=('a',))])
        self.assertEqual(results['a'].state, 'skipped')
        self.assertEqual(seen, ['b'])

    def test_failure_blocks_dependents_and_stops_pending_work(self):
        def fail():
            raise RuntimeError('broken')
        results = run([Task('a', fail), Task('b', lambda: self.fail('must block'), needs=('a',)),
                       Task('c', lambda: self.fail('must not schedule'))], workers=1)
        self.assertEqual([results[n].state for n in ('a', 'b', 'c')], ['failed', 'blocked', 'blocked'])

    def test_invalid_graph_is_rejected_before_work(self):
        for tasks in ([Task('a', None, ('missing',))], [Task('a', None), Task('a', None)],
                      [Task('a', None, ('b',)), Task('b', None, ('a',))]):
            with self.assertRaises(ValueError):
                validate(tasks)

    def test_exclusive_tasks_own_caller_thread(self):
        caller = threading.get_ident()
        results = run([Task('terminal', lambda: self.assertEqual(threading.get_ident(), caller), exclusive=True)])
        self.assertEqual(results['terminal'].state, 'done')

    def test_manifests_validate_and_cover_after_hooks(self):
        for filename in ('home-plan.json', 'workflow.json'):
            plan = json.loads((ROOT / 'scripts/fleet_update' / filename).read_text())
            validate([Task(x['id'], None, tuple(x.get('needs', []))) for x in plan])
        home = json.loads((ROOT / 'scripts/fleet_update/home-plan.json').read_text())
        self.assertEqual({x['file'] for x in home}, {p.name for p in (ROOT / 'home/.chezmoiscripts').glob('run_after_*')})
        for item in home:
            self.assertIn('FLEET_DEFER_HOOKS', (ROOT / 'home/.chezmoiscripts' / item['file']).read_text())


class CacheTests(unittest.TestCase):
    def test_skip_and_repair_modified_missing_or_mode_changed_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_STATE_HOME': directory}):
            root = Path(directory)
            source, output, trace = [root / name for name in ('source', 'output', 'trace')]
            source.write_text('one')
            script = "from pathlib import Path; import sys; s,o,t=map(Path,sys.argv[1:]); o.write_bytes(s.read_bytes()); o.chmod(0o755); t.open('a').write('run\\n')"
            command = [sys.executable, '-c', script, str(source), str(output), str(trace)]
            def install():
                self.assertEqual(cache.cached_install('test', [source], [output], command), 0)
            install(); install()
            self.assertEqual(trace.read_text().count('run'), 1)
            output.unlink(); install()
            output.write_text('drift'); install()
            output.chmod(0o644); install()
            source.write_text('two'); install()
            self.assertEqual(trace.read_text().count('run'), 5)
            self.assertEqual(output.read_text(), 'two')

    def test_failed_install_never_marks_current(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_STATE_HOME': directory}):
            source = Path(directory) / 'source'; source.write_text('source')
            output = Path(directory) / 'output'; output.write_text('partial')
            self.assertEqual(cache.cached_install('test', [source], [output], [sys.executable, '-c', 'exit(2)']), 2)
            self.assertFalse((Path(directory) / 'tjikup/install/test.json').exists())


@unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'Chezmoi and Fish required')
class HookTests(unittest.TestCase):
    def test_all_home_hooks_render_for_each_host(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for host in ('fi', 'li', 'si'):
                config = root / 'config.json'
                config.write_text(json.dumps({'data': dict(isDesktop=host == 'fi', isLaptop=host == 'li',
                    isClient=host != 'si', isServer=host == 'si', paths={'appData': '/synthetic/appdata'})}))
                for hook in (ROOT / 'home/.chezmoiscripts').glob('run_after_*.tmpl'):
                    with self.subTest(host=host, hook=hook.name):
                        # Exercise hostname-specific branches as well as the host flags.
                        template = hook.read_text().replace('.chezmoi.hostname', json.dumps(host))
                        rendered = subprocess.run(['chezmoi', '--config', str(config), '--source', temporary,
                            '--persistent-state', str(root / 'state.db'), 'execute-template'],
                            input=template, text=True, capture_output=True, check=True).stdout
                        subprocess.run(['fish', '--no-config', '--no-execute'], input=rendered,
                                       text=True, capture_output=True, check=True)

    def test_rust_fast_mode_checks_installed_packages_before_network_work(self):
        template = (ROOT / 'home/.chezmoiscripts/run_after_29-rust-packages.fish.tmpl').read_text()
        script = '\n'.join(line for line in template.splitlines() if not line.startswith('source '))
        prelude = """
function section_header; end
function stage_dynamic_note; $argv[4..]; end
function cargo
    if test "$argv[1]" = install; and test "$argv[2]" = --list
        printf 'serie v1.0.0:\n    serie\ndysk v1.0.0:\n    dysk\n'
    else
        echo INSTALL_CALLED
        return 9
    end
end
"""
        with tempfile.TemporaryDirectory() as temporary:
            for name in ('serie', 'dysk'):
                executable = Path(temporary) / name
                executable.write_text('#!/bin/sh\nexit 0\n')
                executable.chmod(0o755)
            for upgrade in ('0', '1'):
                result = subprocess.run(['fish', '--no-config'], input=prelude + script,
                    env={**os.environ, 'FLEET_UPGRADE': upgrade, 'FLEET_DEFER_HOOKS': '0',
                         'PATH': temporary + os.pathsep + os.environ['PATH']},
                    text=True, capture_output=True, timeout=5)
                self.assertEqual('INSTALL_CALLED' in result.stdout, upgrade == '1', result.stderr)
                self.assertEqual(result.returncode, 0 if upgrade == '0' else 9, result.stderr)


if __name__ == '__main__':
    unittest.main()
