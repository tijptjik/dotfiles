"""Merged asset operations report one result and retain private diagnostics."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('asset_setup',ROOT/'scripts/asset-setup.py')
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)

class AssetSetupTests(unittest.TestCase):
    def test_changed_then_current_steps_produce_one_row(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(assets.subprocess,'run',side_effect=[
                subprocess.CompletedProcess([],0,'SYNC    ✓ Assets (user fonts)  migrated\n',''),
                subprocess.CompletedProcess([],0,'SKIP    ✓ Fonts  no changes\n','')]), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(assets.execute('fonts',Path(directory)),0)
            self.assertEqual(output.getvalue(),'APPLY   ✓ Fonts  updated\n')
            log=Path(directory)/'fonts-steps.log'
            self.assertIn('migrated',log.read_text())
            self.assertEqual(log.stat().st_mode & 0o777,0o600)

    def test_step_failure_stops_without_printing_child_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(assets.subprocess,'run',
                return_value=subprocess.CompletedProcess([],4,'PRIVATE-DIAGNOSTIC','')) as run, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(assets.execute('icons',Path(directory)),4)
            self.assertEqual(run.call_count,1)
            self.assertNotIn('PRIVATE-DIAGNOSTIC',output.getvalue())
            self.assertIn('PRIVATE-DIAGNOSTIC',(Path(directory)/'icons-steps.log').read_text())
