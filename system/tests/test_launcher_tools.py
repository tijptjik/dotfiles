"""Verify installer preserves unmanaged commands and updates managed links."""
import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'etc/.chezmoitemplates/install-launcher-tools.py'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etc/.chezmoitemplates'))
spec = importlib.util.spec_from_file_location('launcher_tools', SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class LauncherToolsTests(unittest.TestCase):
    def test_activation_preserves_unmanaged_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = root / 'gitfetch'
            command.write_text('personal executable')
            with patch.object(installer, 'Path', return_value=root):
                with self.assertRaisesRegex(RuntimeError, 'unmanaged command'):
                    installer.activate('gitfetch', root / 'release/gitfetch')
            self.assertEqual(command.read_text(), 'personal executable')

    def test_activation_updates_existing_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = root / 'gitfetch'
            command.symlink_to(root / 'old/gitfetch')
            def run(*args):
                self.assertEqual(args[:2], ('sudo', '-n'))
                if args[2:4] == ('ln', '-sfn'):
                    Path(args[5]).unlink(missing_ok=True)
                    Path(args[5]).symlink_to(args[4])
                elif args[2:4] == ('mv', '-Tf'):
                    Path(args[4]).replace(args[5])
                else:
                    self.fail(f'Unexpected system command: {args}')
            with patch.object(installer, 'Path', side_effect=lambda p: root if p == '/usr/local/bin' else Path(p)), \
                 patch.object(installer, 'run', side_effect=run) as commands:
                self.assertTrue(installer.activate('gitfetch', root / 'new/gitfetch'))
                self.assertEqual(commands.call_count, 2)
                self.assertFalse(installer.activate('gitfetch', root / 'new/gitfetch'))
                self.assertEqual(commands.call_count, 2)
            self.assertEqual(command.readlink(), root / 'new/gitfetch')
