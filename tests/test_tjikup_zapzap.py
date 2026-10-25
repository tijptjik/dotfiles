import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'home/dot_local/lib'))
import tjikup_support
from fleet_update.propagators.zapzap import ZapZapPropagator
from fleet_update.core import UpdateError


class ZapZapTests(unittest.TestCase):
    def test_each_client_preserves_other_clients_and_qt_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, live, output = (Path(tmp)/name for name in ('source', 'live', 'output'))
            source.write_text(json.dumps({'zapzapConfigs': {'fi': 'desktop', 'li': 'laptop'}}))
            for host in ('fi', 'li'):
                before = json.loads(source.read_text())['zapzapConfigs']
                text = '[main]\ngeometry=@ByteArray(\\x1\\0' + host + ')\nwindowState=@Variant(\\0)\n'
                live.write_text(text)
                with patch('fleet_update.propagators.zapzap.socket.gethostname', return_value=host+'.local'):
                    ZapZapPropagator().propagate(source, live, output)
                after = json.loads(output.read_text())['zapzapConfigs']
                self.assertEqual(after[host], text)
                other = 'li' if host == 'fi' else 'fi'
                self.assertEqual(after[other], before[other])
                source.write_text(output.read_text())

    def test_invalid_data_does_not_replace_other_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, live, output = (Path(tmp)/name for name in ('source', 'live', 'output'))
            source.write_text('{"zapzapConfigs": []}')
            live.write_text('settings')
            with self.assertRaises(UpdateError):
                ZapZapPropagator().propagate(source, live, output)
            self.assertFalse(output.exists())
