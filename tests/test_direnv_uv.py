import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


RC = Path(__file__).parents[1] / "home/dot_config/direnv/direnvrc"


class LayoutUvTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        self.other = self.root / "other-env"
        self.other.mkdir()

    def run_layout(self, stub, assertions, inherited=True):
        env = os.environ.copy()
        env.pop("UV_ACTIVE", None)
        env.pop("VIRTUAL_ENV", None)
        if inherited:
            env["VIRTUAL_ENV"] = str(self.other)
        script = f'''
source {shlex.quote(str(RC))}
watch_file() {{ printf '%s\\n' "$@" > watched; }}
log_status() {{ :; }}
log_error() {{ :; }}
PATH_add() {{ export PATH="$1:$PATH"; }}
{stub}
before_path="$PATH"
before_env="${{VIRTUAL_ENV-}}"
layout_uv
result=$?
{assertions}
'''
        result = subprocess.run(["bash", "--noprofile", "--norc", "-c", script],
                                cwd=self.project, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_creates_project_env_ignoring_inherited_env_and_watches_inputs(self):
        self.run_layout('''
uv() {
    [[ "$#" == 2 && "$1" == venv && "$2" == "$PWD/.venv" ]] || return 99
    mkdir -p "$2/bin"
    cp /bin/true "$2/bin/python"
}
''', '''
[[ "$result" == 0 && "$VIRTUAL_ENV" == "$PWD/.venv" && "$UV_ACTIVE" == 1 ]] || exit 1
[[ "$PATH" == "$PWD/.venv/bin:$before_path" ]] || exit 2
''')
        self.assertEqual((self.project / "watched").read_text().splitlines(),
                         ["pyproject.toml", "uv.lock", ".python-version"])

    def test_existing_env_is_reused_without_installing_dependencies(self):
        env_bin = self.project / ".venv/bin"
        env_bin.mkdir(parents=True)
        shutil.copy2("/bin/true", env_bin / "python")
        self.run_layout('uv() { touch unexpected-uv-call; return 99; }', '''
[[ "$result" == 0 && "$VIRTUAL_ENV" == "$PWD/.venv" ]] || exit 1
[[ ! -e unexpected-uv-call ]] || exit 2
''', inherited=False)

    def test_creation_failure_preserves_environment(self):
        self.run_layout('uv() { return 42; }', '''
[[ "$result" == 42 && "$VIRTUAL_ENV" == "$before_env" ]] || exit 1
[[ "$PATH" == "$before_path" && -z "${UV_ACTIVE-}" ]] || exit 2
''')

    def test_missing_uv_fails_before_exporting(self):
        self.run_layout('command() { return 1; }', '''
[[ "$result" != 0 && "$VIRTUAL_ENV" == "$before_env" ]] || exit 1
[[ "$PATH" == "$before_path" && -z "${UV_ACTIVE-}" ]] || exit 2
''')

    def test_incomplete_existing_env_fails_without_replacing_it(self):
        (self.project / ".venv").mkdir()
        self.run_layout('uv() { touch unexpected-uv-call; return 0; }', '''
[[ "$result" != 0 && "$VIRTUAL_ENV" == "$before_env" ]] || exit 1
[[ "$PATH" == "$before_path" && ! -e unexpected-uv-call ]] || exit 2
''')
