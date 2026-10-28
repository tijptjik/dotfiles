import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etc/.chezmoitemplates'))
spec = importlib.util.spec_from_file_location('installer', ROOT/'etc/.chezmoitemplates/install-tippecanoe.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class TippecanoeTests(unittest.TestCase):
    def test_only_stable_version_tags_are_accepted(self):
        self.assertEqual(installer.release_tag({'tag_name': '2.79.0'}), '2.79.0')
        for data in [{'tag_name': '../../bad'}, {'tag_name': 'v2.79.0', 'prerelease': True},
                     {'tag_name': '2.79.0', 'draft': True}, {}]:
            with self.assertRaises(RuntimeError): installer.release_tag(data)

    def test_partial_install_is_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            (prefix/'revision').write_text('abc')
            self.assertFalse(installer.current_install(prefix))
            (prefix/'bin').mkdir()
            for name in installer.TOOLS:
                p = prefix/'bin'/name
                p.write_text('binary'); p.chmod(0o755)
            self.assertTrue(installer.current_install(prefix))

    def test_collision_is_detected_before_any_launcher_changes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(installer, 'run') as run:
            directory = Path(tmp)
            (directory/installer.TOOLS[-1]).write_text('unmanaged')
            with self.assertRaisesRegex(RuntimeError, 'unmanaged'):
                installer.activate(Path('/opt/example'), directory)
            run.assert_not_called()
