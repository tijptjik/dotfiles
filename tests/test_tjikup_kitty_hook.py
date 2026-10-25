"""Keep Kitty's fallback when the optional local runner bridge is unavailable."""

from pathlib import Path
import runpy
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


class KittyHookTests(unittest.TestCase):
    def test_bridge_result_and_import_path_cleanup(self):
        hook = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                                  'home/dot_config/kitty/notifications.py'))['main']
        for result in (True, False, ImportError('old runner')):
            module = ModuleType('tjikup.notifications')
            bridge = Mock(**({'side_effect': result} if isinstance(result, Exception)
                             else {'return_value': result}))
            module.ssh_notification_filter = bridge
            paths = sys.path[:]
            with patch.dict(sys.modules, {'tjikup.notifications': module}):
                command = object()
                self.assertEqual(hook(command), result if isinstance(result, bool) else False)
                bridge.assert_called_once_with(command)
            self.assertEqual(sys.path, paths)
