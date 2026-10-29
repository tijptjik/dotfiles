import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("snapraid_maintenance", ROOT / "tests/legacy/protection/maintenance.py")
maintenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maintenance)

class ReadabilityTests(unittest.TestCase):
    def test_busy_maintenance_is_deferred_without_commands_or_writes(self):
        with patch("builtins.open", mock_open()), patch.object(maintenance.fcntl, "flock", side_effect=BlockingIOError), patch.object(maintenance, "guard") as guard, patch.object(maintenance, "run") as run, patch.object(maintenance, "save") as save:
            self.assertEqual(maintenance.verify_status(), 75)
            guard.assert_not_called()
            run.assert_not_called()
            save.assert_not_called()

    def test_check_only_reads_status_after_storage_guard(self):
        config = MagicMock()
        config.read_text.return_value = json.dumps({"mounts": {}})
        with patch("builtins.open", mock_open()), patch.object(maintenance.fcntl, "flock"), patch.object(maintenance, "CONFIG", config), patch.object(maintenance, "guard") as guard, patch.object(maintenance, "run") as run, patch.object(maintenance, "save") as save:
            self.assertEqual(maintenance.verify_status(), 0)
            guard.assert_called_once_with({"mounts": {}})
            run.assert_called_once_with(["snapraid", "status"])
            save.assert_not_called()

    def test_incompatible_content_fails_instead_of_triggering_conversion(self):
        config = MagicMock()
        config.read_text.return_value = "{}"
        with patch("builtins.open", mock_open()), patch.object(maintenance.fcntl, "flock"), patch.object(maintenance, "CONFIG", config), patch.object(maintenance, "guard"), patch.object(maintenance, "run", side_effect=subprocess.CalledProcessError(1, ["snapraid", "status"])) as run, patch.object(maintenance, "save") as save:
            with self.assertRaises(subprocess.CalledProcessError):
                maintenance.verify_status()
            self.assertEqual(run.call_count, 1)
            save.assert_not_called()

if __name__ == "__main__":
    unittest.main()
