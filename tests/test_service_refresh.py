"""Service updates must activate new bytes and preserve stopped services/jobs."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("service_refresh", ROOT / "scripts/refresh-user-services.py")
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)


class ServiceRefreshTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state = self.root / "state.json"
        self.code = self.root / "runtime"
        self.code.mkdir()
        (self.code / "main.py").write_text("old code\n")
        self.units = {"notjik.service": [str(self.code)], "bartjik.service": [str(self.code)]}
        self.active = {unit: "active" for unit in self.units}
        self.types = {}
        self.definitions = {}
        self.calls = []
        self.fail = None
        self.crash = None
        self.mutate = False
        self.patcher = patch.object(refresh, "systemctl", side_effect=self.systemctl)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def systemctl(self, *args):
        self.calls.append(args)
        if args[0] == "show":
            unit = args[1]
            return (f"LoadState=loaded\nActiveState={self.active[unit]}\n"
                    f"Type={self.types.get(unit, 'simple')}\nExecStart=\n")
        if args[0] == "cat":
            return self.definitions.get(args[1], "[Service]\nExecStart=example\n")
        if args[0] == "try-restart":
            if args[1] == self.fail:
                raise subprocess.CalledProcessError(1, args, stderr="startup failed")
            if args[1] == self.crash:
                self.active[args[1]] = "failed"
            if self.mutate:
                (self.code / "main.py").write_text("concurrent install\n")
        return ""

    def run_refresh(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            refresh.refresh(self.units, self.state, **kwargs)

    def restarts(self):
        return [args[1] for args in self.calls if args[0] == "try-restart"]

    def test_initial_refresh_then_identical_reinstall_skips(self):
        self.run_refresh()
        self.assertEqual(self.restarts(), list(self.units))
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        self.calls.clear()
        (self.code / "main.py").write_text("old code\n")
        self.run_refresh()
        self.assertEqual(self.restarts(), [])

    def test_unchanged_runtime_reports_skip_without_reloading_manager(self):
        self.run_refresh()
        self.calls.clear()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            refresh.refresh(self.units, self.state)
        self.assertIn('__stage_verb__:SKIP', output.getvalue())
        self.assertIn('__stage_note__:no runtime changes', output.getvalue())
        self.assertNotIn(('daemon-reload',), self.calls)
        self.assertEqual(self.restarts(), [])

    def test_post_update_hides_only_unchanged_service_rows(self):
        self.run_refresh()
        self.calls.clear()
        with patch.dict(refresh.os.environ, {'TJIKUP_HIDE_UNCHANGED_SERVICES': '1', 'TJIKUP_SERVICE_SECTION': 'Verification'}), contextlib.redirect_stdout(io.StringIO()) as output:
            refresh.refresh(self.units, self.state)
        self.assertNotIn('runtime unchanged', output.getvalue())
        self.assertIn('__tjikup_section__:Verification', output.getvalue())
        self.assertEqual(self.restarts(), [])
        (self.code / 'main.py').write_text('updated code')
        with patch.dict(refresh.os.environ, {'TJIKUP_HIDE_UNCHANGED_SERVICES': '1'}), contextlib.redirect_stdout(io.StringIO()) as output:
            refresh.refresh(self.units, self.state)
        self.assertIn('notjik.service  updated runtime active', output.getvalue())
        self.assertEqual(set(self.restarts()), set(self.units))

    def test_runtime_and_unit_changes_refresh_only_affected_units(self):
        self.run_refresh()
        self.calls.clear()
        self.definitions["bartjik.service"] = "[Service]\nExecStart=new-wrapper\n"
        self.run_refresh()
        self.assertEqual(self.restarts(), ["bartjik.service"])
        self.calls.clear()
        (self.code / "main.py").write_text("new code\n")
        self.run_refresh()
        self.assertEqual(self.restarts(), list(self.units))

    def test_stopped_services_are_never_started_or_acknowledged(self):
        self.active = dict.fromkeys(self.units, "inactive")
        self.run_refresh()
        self.assertEqual(self.restarts(), [])
        self.assertFalse(self.state.exists())
        self.assertFalse(any(args[0] == "cat" for args in self.calls))

    def test_failed_restart_retries_without_repeating_successful_units(self):
        self.fail = "bartjik.service"
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_refresh()
        self.assertEqual(set(json.loads(self.state.read_text())), {"notjik.service"})
        self.calls.clear()
        self.fail = None
        self.run_refresh()
        self.assertEqual(self.restarts(), ["bartjik.service"])

    def test_inactive_after_restart_does_not_record_success(self):
        self.crash = "notjik.service"
        with self.assertRaisesRegex(RuntimeError, "did not become active"):
            self.run_refresh()
        self.assertFalse(self.state.exists())

    def test_concurrent_install_does_not_record_success(self):
        self.mutate = True
        with self.assertRaisesRegex(RuntimeError, "inputs changed"):
            self.run_refresh()
        self.assertFalse(self.state.exists())

    def test_preview_changes_neither_services_nor_state(self):
        self.run_refresh(check=True)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.restarts(), [])
        self.assertNotIn(("daemon-reload",), self.calls)

    def test_timer_refresh_does_not_restart_its_running_job(self):
        self.units = {"backup.timer": []}
        self.active["backup.timer"] = "active"
        self.run_refresh()
        self.assertEqual(self.restarts(), ["backup.timer"])

    def test_job_cannot_be_added_to_restart_inventory(self):
        self.types["notjik.service"] = "oneshot"
        with self.assertRaisesRegex(ValueError, "Refusing to restart job"):
            self.run_refresh()
        self.assertEqual(self.restarts(), [])

    def test_bytecode_does_not_trigger_restart_but_symlink_target_does(self):
        target = self.root / "installed-version"
        target.write_text("version one")
        (self.code / "linked.py").symlink_to(target)
        self.run_refresh()
        self.calls.clear()
        cache = self.code / "__pycache__"
        cache.mkdir()
        (cache / "main.pyc").write_bytes(b"cache")
        self.run_refresh()
        self.assertEqual(self.restarts(), [])
        target.write_text("version two")
        self.run_refresh()
        self.assertEqual(self.restarts(), list(self.units))

    def test_entrypoint_changes_are_included_without_extra_inputs(self):
        binary = self.root / "daemon"
        binary.write_bytes(b"version one")
        info = {"ExecStart": f"{{ path={binary} ; argv[]={binary} ; }}"}
        before = refresh.fingerprint("notjik.service", [], info)
        binary.write_bytes(b"version two")
        self.assertNotEqual(refresh.fingerprint("notjik.service", [], info), before)

    def test_missing_unit_is_skipped_but_bus_errors_propagate(self):
        with patch.object(refresh, "systemctl", side_effect=subprocess.CalledProcessError(
                1, "show", output="LoadState=not-found\nActiveState=inactive\n")):
            self.assertEqual(refresh.properties("absent.service")["LoadState"], "not-found")
        with patch.object(refresh, "systemctl", side_effect=subprocess.CalledProcessError(
                1, "show", stderr="Failed to connect to bus")):
            with self.assertRaises(subprocess.CalledProcessError):
                refresh.properties("notjik.service")


if __name__ == "__main__":
    unittest.main()
