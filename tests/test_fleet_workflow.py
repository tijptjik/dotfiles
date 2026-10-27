"""Run the configured fleet in a temporary home with stub Git/apply commands."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import tjikup_support
import tjikup
from fleet_update import discover_propagators

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
        shutil.copy(REPO / "tjikup.json", self.repo / "tjikup.json")
        (system / "scripts").mkdir()
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
    if sys.argv[1] == 'diff': print('home/dot_config/fcitx5/private_profile')
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
        }

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
            "Tijpfiles\nhttps://github.com/tijptjik/dotfiles",
            "Prerequisites\n",
            "Commit Local Changes\n",
            "Dotfiles Repository\n",
            "Dotfiles Apply\n",
            "Tijpcetera\nhttps://github.com/tijptjik/etcfiles",
        ]
        positions = [result.stdout.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        rows = result.stdout.splitlines()
        self.assertEqual(sum(row.startswith("COMMIT") for row in rows), 1)
        self.assertFalse(any(row.startswith("CHECK") and "Prerequisites" in row for row in rows))
        self.assertNotIn("Live configuration", result.stdout)
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

    def add_synthetic_hooks(self):
        plan = json.loads((REPO / 'scripts/fleet_update/home-plan.json').read_text())
        hooks = self.repo / 'home/.chezmoiscripts'
        hooks.mkdir(parents=True)
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
import os, pathlib, subprocess, sys
if 'execute-template' in sys.argv:
    print(pathlib.Path(sys.argv[-1]).read_text(), end='')
else:
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

    def test_hook_failure_blocks_system_apply(self):
        self.add_synthetic_hooks()
        self.env['FAIL_HOOK'] = '1'
        result = self.run_fleet()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('chezetc', [row[0] for row in self.events()])
        calls = Path(self.env['HOOK_TRACE']).read_text().splitlines()
        self.assertFalse(any('llmtrim' in name for name in calls))
