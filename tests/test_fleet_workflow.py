"""Run the configured fleet in a temporary home with stub Git/apply commands."""

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
import tjikup
from fleet_update import discover_propagators
from fleet_update.workflow import show_failure

REPO = Path(__file__).resolve().parents[1]


class FleetWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="fleet-workflow-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.repo = self.home / ".local/share/chezmoi"
        system = self.home / ".local/share/chezetc"
        for repo in (self.repo, system):
            (repo / ".git").mkdir(parents=True)
        shutil.copytree(
            REPO / "scripts/fleet_update", self.repo / "scripts/fleet_update"
        )
        shutil.copy(
            REPO / "scripts/fleet-update.py", self.repo / "scripts/fleet-update.py"
        )
        shutil.copy(
            REPO / "scripts/tjikup_dependency.py", self.repo / "scripts/tjikup_dependency.py"
        )
        shutil.copy(REPO / "tjikup.json", self.repo / "tjikup.json")
        (system / "scripts").mkdir()
        for name in ('tjikup-plan.py', 'tjikup-plan.json'):
            shutil.copy(REPO.parent / 'chezetc/scripts' / name, system / 'scripts' / name)
        system_hooks = system / 'etc/.chezmoiscripts'
        system_hooks.mkdir(parents=True)
        system_plan = json.loads((system / 'scripts/tjikup-plan.json').read_text())
        for item in system_plan:
            (system_hooks / item['file']).write_text(
                'if test "$FLEET_DEFER_SYSTEM_HOOKS" = 1; exit 0; end\n'
                'printf "%s:%s\\n" "' + item['file'] + '" "$FLEET_SYSTEM_PHASE" >> "$SYSTEM_TRACE"\n')
        shutil.copy(
            REPO.parent / "chezetc/scripts/tjikup-apply.py",
            system / "scripts/tjikup-apply.py",
        )
        for propagator in discover_propagators():
            path = self.repo / propagator.source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("original\n")
        target = self.home / ".config/fcitx5/profile"
        target.parent.mkdir(parents=True)
        target.write_text("captured live settings\n")
        self.source = self.repo / "home/dot_config/fcitx5/private_profile"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        script = (
            f"#!{sys.executable}\n"
            + """import json, os, pathlib, sys
with open(os.environ['TRACE'], 'a') as stream:
    stream.write(json.dumps([pathlib.Path(sys.argv[0]).name, pathlib.Path.cwd().name, sys.argv[1:]]) + '\\n')
if pathlib.Path(sys.argv[0]).name == 'git':
    if sys.argv[1] == 'rev-list': print('0')
    if sys.argv[1] == 'status' and pathlib.Path.cwd().name == os.environ.get('DIRTY_REPO'):
        print('?? personal-work')
    if sys.argv[1] == 'diff': print('home/dot_config/fcitx5/private_profile')
    if sys.argv[1] == 'pull' and pathlib.Path.cwd().name == 'chezmoi':
        failure = os.environ.get('FAIL_PULL')
        if failure == 'conflict':
            print('Created autostash: 1d36f4a')
            print('CONFLICT (content): Merge conflict in home/dot_config/herdr/session.json.tmpl')
            print('Rebasing (3/3)', file=sys.stderr)
            print('error: could not apply 56f8046... sync: update templates', file=sys.stderr)
            print('hint: Resolve all conflicts manually', file=sys.stderr)
            raise SystemExit(1)
        if failure == 'auth':
            print('Permission denied (publickey).', file=sys.stderr)
            print('fatal: Could not read from remote repository.', file=sys.stderr)
            raise SystemExit(1)
if pathlib.Path(sys.argv[0]).name == 'chezmoi' and os.environ.get('FAIL_HOME'):
    print('intentional home failure', file=sys.stderr); raise SystemExit(8)
"""
        )
        for name in ("git", "chezmoi", "chezetc"):
            executable = self.bin / name
            executable.write_text(script)
            executable.chmod(0o755)
        self.trace = self.root / "trace"
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "PYTHONPATH": str(Path(tjikup.__file__).resolve().parents[1]),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_STATE_HOME": str(self.home / ".local/state"),
            "TJIKUP_NOTIFY": "0",
            "TRACE": str(self.trace),
            "SYSTEM_TRACE": str(self.root / "system-hooks.log"),
        }
        self.env.pop('TJIKOS_REPO', None)
        self.add_synthetic_hooks()
        # Root command boundary is stubbed; no test can invoke real sudo.
        sudo = self.bin / 'sudo'
        sudo.write_text(f'#!{sys.executable}\n' + """
import os, sys
args = sys.argv[1:]
if args == ['-n', 'true']:
    raise SystemExit(0)
args = args[args.index('--') + 1:]
os.execvp(args[0], args)
""")
        sudo.chmod(0o755)
        chezetc = self.bin / 'chezetc'
        chezetc.write_text(f'#!{sys.executable}\n' + """
import json, os, pathlib, re, subprocess, sys
if 'execute-template' in sys.argv:
    if os.environ.get('FAIL_SYSTEM_RENDER'):
        print('broken system rendering', file=sys.stderr); raise SystemExit(8)
    directory = pathlib.Path(sys.argv[sys.argv.index('--source') + 1]) / '.chezmoiscripts'
    names = re.findall(r'includeTemplate "[.]chezmoiscripts/([^"]+)"', sys.stdin.read())
    print(json.dumps({name: (directory / name).read_text() for name in names}))
else:
    with open(os.environ['TRACE'], 'a') as stream:
        stream.write(json.dumps(['chezetc', pathlib.Path.cwd().name, sys.argv[1:]]) + '\\n')
    if os.environ.get('FAIL_SYSTEM'):
        print('intentional system file failure', file=sys.stderr); raise SystemExit(8)
    hooks = pathlib.Path(sys.argv[sys.argv.index('--source') + 1]) / '.chezmoiscripts'
    for hook in sorted(hooks.iterdir()):
        subprocess.run(['fish', '--no-config', str(hook)], check=True)
""")
        chezetc.chmod(0o755)

    def run_fleet(self, *flags):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "tjikup",
                "--config",
                str(self.repo / "tjikup.json"),
                *flags,
            ],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def events(self):
        return (
            [json.loads(line) for line in self.trace.read_text().splitlines()]
            if self.trace.exists()
            else []
        )

    def test_preview_has_no_git_apply_source_or_backup_mutations(self):
        result = self.run_fleet("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("captured live settings", result.stdout)
        self.assertEqual(self.source.read_text(), "original\n")
        self.assertEqual(self.events(), [])
        self.assertFalse((self.home / ".local/state/tjikup/backups").exists())

    def test_real_workflow_captures_scoped_commit_and_applies_in_order(self):
        result = self.run_fleet("--skip-conflicts")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.source.read_text(), "captured live settings\n")
        self.assertTrue(
            list((self.home / ".local/state/tjikup/backups/fcitx").glob("*.backup"))
        )
        headings = [
            "Dotjik\nhttps://github.com/tijptjik/dotfiles",
            "Prerequisites\n",
            "Commit Local Changes\n",
            "Fleet repositories\n",
            "Dotfiles Apply\n",
            "Home + system tasks\n",
        ]
        positions = [result.stdout.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("Systjik\nhttps://github.com/tijptjik/systjik", result.stdout)
        rows = result.stdout.splitlines()
        report = next(i for i, row in enumerate(rows) if row.startswith("Task timings:"))
        self.assertEqual(rows[report - 1], "")
        self.assertTrue(rows[report - 2].startswith("APPLY"), result.stdout)
        self.assertIn("Home and system", rows[report - 2])
        self.assertFalse(any(row.startswith("APPLY") and "Home and system" in row
                             for row in rows[report + 1:]))
        self.assertEqual(sum(row.startswith("COMMIT") for row in rows), 1)
        self.assertFalse(any(row.startswith("CHECK") and "Prerequisites" in row for row in rows))
        self.assertNotIn("Live configuration", result.stdout)
        self.assertNotIn("DAG     ", result.stdout)
        self.assertIn("dotjik    PULL [unchanged]  PUSH [unchanged]", result.stdout)
        self.assertIn("systjik   PULL [unchanged]  PUSH [unchanged]", result.stdout)
        self.assertIn("tjikOS    PULL [blocked]  PUSH [blocked]", result.stdout)
        events = self.events()
        commit = next(
            row for row in events if row[0] == "git" and row[2][0] == "commit"
        )
        self.assertIn("--only", commit[2])
        self.assertEqual(commit[2][-1], "home/dot_config/fcitx5/private_profile")
        applies = [row for row in events if row[0] != "git"]
        self.assertEqual([row[0] for row in applies], ["chezmoi", "chezetc"])
        for row in applies:
            self.assertIn("--no-tty", row[2])
            self.assertIn("--source", row[2])

    def test_home_failure_blocks_system_apply(self):
        self.env["FAIL_HOME"] = "1"
        result = self.run_fleet()
        self.assertEqual(result.returncode, 1)
        self.assertIn("intentional home failure", result.stderr)
        self.assertNotIn("chezetc", [row[0] for row in self.events()])

    def test_dirty_configuration_repositories_fail_and_block_apply(self):
        for checkout, label in (("chezmoi", "dotjik"), ("chezetc", "systjik")):
            with self.subTest(checkout=checkout):
                self.trace.unlink(missing_ok=True)
                self.env.update(DIRTY_REPO=checkout, TJIKUP_COLOR="0")
                result = self.run_fleet()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(f"{label:<8}  PULL [failed]", result.stdout)
                repository_row = next(row for row in result.stdout.splitlines()
                                      if row.startswith(f'{label:<8}  PULL [failed]'))
                self.assertTrue(repository_row.endswith('1 file'), repository_row)
                self.assertNotIn('dirty checkout', result.stdout)
                self.assertNotIn('Log:', result.stdout)
                inline, _, end_summary = result.stdout.partition('NEEDS ATTENTION')
                self.assertNotIn('commit or stash them first', inline)
                self.assertIn(f'PULL    ✗ {label.title()} has changes - commit or stash them first', end_summary)
                self.assertNotIn('Dirty', result.stdout)
                self.assertFalse(list((self.home / '.local/state/tjikup/logs').glob('pull-*.log')))
                self.assertNotIn("Apply Home and system", result.stdout)
                self.assertFalse(any(row[0] in {"chezmoi", "chezetc"} for row in self.events()))
                self.assertFalse(any(row[0] == "git" and row[1] == checkout
                                     and row[2][0] in {"pull", "push"} for row in self.events()))

    def test_tjikos_failure_blocks_all_apply(self):
        path = self.repo / 'scripts/fleet_update/workflow.json'
        plan = json.loads(path.read_text())
        for step in plan:
            if step['id'] == 'pull-tjikos':
                step['command'] = [sys.executable, '-c', 'raise SystemExit(9)']
        path.write_text(json.dumps(plan))
        result = self.run_fleet()
        self.assertEqual(result.returncode, 1)
        self.assertIn('tjikOS', result.stdout)
        self.assertFalse(any(row[0] in {'chezmoi', 'chezetc'} for row in self.events()))

    def test_tjikos_push_failure_blocks_apply(self):
        path = self.repo / 'scripts/fleet_update/workflow.json'
        plan = json.loads(path.read_text())
        for step in plan:
            if step['id'] == 'push-tjikos':
                step['command'] = [sys.executable, '-c', 'raise SystemExit(9)']
        path.write_text(json.dumps(plan))
        result = self.run_fleet()
        self.assertEqual(result.returncode, 1)
        self.assertIn('tjikOS    PULL [blocked]  PUSH [failed]', result.stdout)
        self.assertFalse(any(row[0] in {'chezmoi', 'chezetc'} for row in self.events()))

    def test_committed_tjikos_changes_are_pushed_before_apply(self):
        checkout = self.home / 'code/tjikos'
        checkout.parent.mkdir(parents=True)
        remote = self.root / 'tjikos.git'
        environment = {**self.env, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                       'GIT_AUTHOR_NAME': 'Test', 'GIT_AUTHOR_EMAIL': 'test@example.org',
                       'GIT_COMMITTER_NAME': 'Test', 'GIT_COMMITTER_EMAIL': 'test@example.org'}

        def git(*arguments):
            return subprocess.check_output(['/usr/bin/git', *arguments], env=environment,
                                           text=True, stderr=subprocess.STDOUT).strip()

        git('init', '--bare', str(remote))
        git('init', '-b', 'main', str(checkout))
        (checkout / 'file').write_text('initial')
        git('-C', str(checkout), 'add', '.')
        git('-C', str(checkout), 'commit', '-m', 'initial')
        git('-C', str(checkout), 'remote', 'add', 'origin', str(remote))
        git('-C', str(checkout), 'push', '-u', 'origin', 'main')
        (checkout / 'file').write_text('development')
        git('-C', str(checkout), 'commit', '-am', 'development')
        # Only tjikOS uses real Git, with a temporary local bare remote.
        stub = self.bin / 'git'
        source = stub.read_text().replace(
            "if pathlib.Path(sys.argv[0]).name == 'git':",
            "if pathlib.Path.cwd().name == 'tjikos':\n"
            "    os.execv('/usr/bin/git', ['git', *sys.argv[1:]])\n"
            "if pathlib.Path(sys.argv[0]).name == 'git':")
        stub.write_text(source)
        self.env.update(environment, TJIKOS_REPO=str(checkout))
        result = self.run_fleet()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(git('-C', str(remote), 'rev-parse', 'main'),
                         git('-C', str(checkout), 'rev-parse', 'HEAD'))
        self.assertIn('tjikOS    PULL [unchanged]  PUSH [changed]', result.stdout)
        events = self.events()
        push = next(i for i, row in enumerate(events)
                    if row[:2] == ['git', 'tjikos'] and row[2] == ['push'])
        apply = next(i for i, row in enumerate(events) if row[0] in {'chezmoi', 'chezetc'})
        self.assertLess(push, apply)
        self.assertFalse(any(row[:2] == ['git', 'tjikos'] and row[2][0] == 'commit'
                             for row in events))

    def test_pull_conflict_is_grouped_and_full_output_is_saved(self):
        self.env.update(FAIL_PULL="conflict", TJIKUP_COLUMNS="80", TJIKUP_COLOR="0")
        result = self.run_fleet()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("dotjik    PULL [failed]", result.stdout)
        self.assertIn("merge conflict", result.stdout)
        self.assertIn("home/dot_config/herdr/session.json.tmpl", result.stdout)
        self.assertIn("git rebase --continue", result.stdout)
        self.assertLess(result.stdout.index("dotjik    PULL [failed]"), result.stdout.index("CONFLICT"))
        self.assertNotIn("Created autostash", result.stdout + result.stderr)
        self.assertNotIn("hint:", result.stdout + result.stderr)
        self.assertNotIn("fleet-update:", result.stdout + result.stderr)
        self.assertNotIn("DAG     ", result.stdout)
        logs = list((self.home / ".local/state/tjikup/logs").glob("pull-home-*.log"))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].stat().st_mode & 0o777, 0o600)
        log = logs[0].read_text()
        self.assertIn("Created autostash: 1d36f4a", log)
        self.assertIn("hint: Resolve all conflicts manually", log)
        self.assertIn("fleet-update: command failed (1)", log)
        self.assertFalse(any(row[0] in {"chezmoi", "chezetc"} for row in self.events()))

    def test_other_git_failures_keep_the_reason_without_rebase_advice(self):
        self.env.update(FAIL_PULL="auth", TJIKUP_COLOR="0")
        result = self.run_fleet()
        self.assertEqual(result.returncode, 1)
        self.assertIn("fatal: Could not read from remote repository.", result.stdout)
        self.assertNotIn("git rebase --continue", result.stdout)
        self.assertNotIn("merge conflict", result.stdout)

    def test_log_write_failure_preserves_all_diagnostics(self):
        output = io.StringIO()
        transcript = "first diagnostic\nsecond diagnostic\n"
        with patch("fleet_update.workflow.tempfile.mkstemp", side_effect=OSError("disk full")), \
                patch.dict(os.environ, self.env), contextlib.redirect_stdout(output):
            show_failure({"id": "pull-home", "verb": "PULL", "label": "Dotjik"},
                         transcript, self.repo, RuntimeError("failed"), 1)
        self.assertIn("Could not save log: disk full", output.getvalue())
        for line in transcript.splitlines():
            self.assertIn(line, output.getvalue())

    def add_synthetic_hooks(self):
        plan = json.loads((REPO / 'scripts/fleet_update/home-plan.json').read_text())
        hooks = self.repo / 'home/.chezmoiscripts'
        hooks.mkdir(parents=True, exist_ok=True)
        for task in plan:
            name = task['file']
            if name.endswith('.py'):
                content = "import os\nif os.environ.get('FLEET_DEFER_HOOKS') == '1': raise SystemExit(0)\n"
                content += f"with open(os.environ['HOOK_TRACE'], 'a') as stream: stream.write({name!r} + '\\n')\n"
            else:
                content = 'if test "$FLEET_DEFER_HOOKS" = 1; exit 0; end\n'
                if task['id'] == 'rust':
                    content += 'if test "$FAIL_HOOK" = 1; exit 9; end\n'
                content += f'printf "%s\\n" "{name}" >> "$HOOK_TRACE"\n'
            (hooks / name).write_text(content)
        self.env['HOOK_TRACE'] = str(self.root / 'hooks.log')
        executable = self.bin / 'chezmoi'
        executable.write_text(f'#!{sys.executable}\n' + """
import json, os, pathlib, subprocess, sys
if 'execute-template' in sys.argv:
    print(pathlib.Path(sys.argv[-1]).read_text(), end='')
else:
    with open(os.environ['TRACE'], 'a') as stream:
        stream.write(json.dumps(['chezmoi', pathlib.Path.cwd().name, sys.argv[1:]]) + '\\n')
    if os.environ.get('FAIL_HOME'):
        print('intentional home failure', file=sys.stderr); raise SystemExit(8)
    hooks = pathlib.Path(sys.argv[sys.argv.index('--source') + 1]) / '.chezmoiscripts'
    for hook in sorted(hooks.iterdir()):
        interpreter = ['python3'] if hook.name.endswith('.py') else ['fish', '--no-config']
        subprocess.run([*interpreter, str(hook)], check=True)
""")
        return plan

    def test_deferred_hooks_run_exactly_once(self):
        plan = self.add_synthetic_hooks()
        result = self.run_fleet()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = Path(self.env['HOOK_TRACE']).read_text().splitlines()
        self.assertCountEqual(calls, [task['file'] for task in plan])
        self.assertIn('chezetc', [row[0] for row in self.events()])

    def test_system_files_failure_blocks_every_deferred_system_hook(self):
        self.env['FAIL_SYSTEM'] = '1'
        result = self.run_fleet()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(Path(self.env['SYSTEM_TRACE']).exists())
        self.assertIn('intentional system file failure', result.stderr + result.stdout)
        rows = result.stdout.splitlines()
        report = next(i for i, row in enumerate(rows) if row.startswith('Task timings:'))
        self.assertEqual(rows[report - 1], '')
        completion = next(row for row in reversed(rows[:report]) if row.startswith('APPLY'))
        self.assertIn('✗', completion)
        self.assertIn('Home and system', completion)

    def test_system_render_failure_blocks_every_deferred_system_hook(self):
        self.env['FAIL_SYSTEM_RENDER'] = '1'
        result = self.run_fleet()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(Path(self.env['SYSTEM_TRACE']).exists())
        self.assertIn('broken system rendering', result.stderr + result.stdout)

    def test_system_hooks_and_package_phases_run_exactly_once(self):
        result = self.run_fleet()
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads((self.home / '.local/share/chezetc/scripts/tjikup-plan.json').read_text())
        self.assertCountEqual(Path(self.env['SYSTEM_TRACE']).read_text().splitlines(),
            [item['file'] + ':' + item.get('env', {}).get('FLEET_SYSTEM_PHASE', '') for item in plan])
        reports = list((self.home / '.local/state/tjikup/logs').glob('apply-*/timings.json'))
        self.assertEqual(len(reports), 1)
        records = json.loads(reports[0].read_text())['tasks']
        self.assertTrue(all(row['state'] == 'done' for row in records))
        self.assertTrue(any(row['id'].startswith('home:') for row in records))
        self.assertTrue(any(row['id'].startswith('system:') for row in records))

    def test_hook_failure_blocks_final_system_release(self):
        self.add_synthetic_hooks()
        self.env['FAIL_HOOK'] = '1'
        result = self.run_fleet()
        self.assertNotEqual(result.returncode, 0)
        system_calls = Path(self.env['SYSTEM_TRACE'])
        if system_calls.exists():
            self.assertFalse(any(line.endswith(':release') for line in system_calls.read_text().splitlines()))
        calls = Path(self.env['HOOK_TRACE']).read_text().splitlines()
        self.assertFalse(any('llmtrim' in name for name in calls))
