"""Exercise the current Python updater without network or privileged writes."""
import importlib.util
import sys
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'etc/.chezmoitemplates/update-client-cli-releases.py'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etc/.chezmoitemplates'))
spec = importlib.util.spec_from_file_location('hyprvoice_updater', SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class HyprvoiceInstallerTests(unittest.TestCase):
    def test_unsupported_architecture_does_not_install(self):
        with patch.object(installer.os, 'uname', return_value=SimpleNamespace(machine='aarch64')), \
             patch.object(installer, 'install') as install:
            with self.assertRaisesRegex(RuntimeError, 'x86_64'):
                installer.main()
            install.assert_not_called()

    def test_bad_checksum_preserves_existing_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'opt/hyprvoice/1.0.0/hyprvoice'
            old.parent.mkdir(parents=True)
            old.write_bytes(b'existing executable')
            link = root / 'bin/hyprvoice'
            link.parent.mkdir()
            link.symlink_to(old)
            def local_path(value):
                return {'/usr/local/bin': root / 'bin', '/opt': root / 'opt'}.get(str(value), Path(value))
            release = ('2.0.0', 'v2.0.0', 'https://example.invalid/hyprvoice', '0' * 64)
            with patch.object(installer, 'Path', side_effect=local_path), \
                 patch.object(installer, 'resolve_release', return_value=release), \
                 patch.object(installer, 'current_install', return_value=('1.0.0', old)), \
                 patch.object(installer.urllib.request, 'urlopen', return_value=io.BytesIO(b'corrupt')), \
                 patch.object(installer, 'run') as privileged, \
                 patch.object(installer.subprocess, 'run') as execute:
                with self.assertRaisesRegex(RuntimeError, 'SHA-256 mismatch'):
                    installer.install('hyprvoice', *installer.SPECS['hyprvoice'])
                privileged.assert_not_called()
                execute.assert_not_called()
                request = installer.urllib.request.urlopen.call_args.args[0]
                self.assertIsNone(request.get_header('Authorization'))
            self.assertEqual(link.readlink(), old)
            self.assertEqual(old.read_bytes(), b'existing executable')
            self.assertFalse((root / 'opt/hyprvoice/2.0.0').exists())
