"""GTK history must never leak between per-host bookmark lists."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'home/dot_local/lib'))
import tjikup_support
from fleet_update.propagators.gtk_bookmarks import PROPAGATOR


class GtkBookmarksTests(unittest.TestCase):
    def test_capture_preserves_other_devices_and_empty_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, target, output = (root / name for name in ('source', 'live', 'output'))
            data = {'gtkBookmarks': {'fi': 'old\n', 'li': 'file:///laptop Laptop\n'}, 'unrelated': 1}
            source.write_text(json.dumps(data))
            for live in ['file:///home/io/My%20Files 圖片\n', '']:
                target.write_text(live)
                with patch('fleet_update.propagators.gtk_bookmarks.socket.gethostname', return_value='fi'):
                    PROPAGATOR.propagate(source, target, output)
                saved = json.loads(output.read_text())
                self.assertEqual(saved['gtkBookmarks'], {'fi': live, 'li': data['gtkBookmarks']['li']})
                self.assertEqual(saved['unrelated'], 1)
                self.assertEqual(json.loads(source.read_text()), data)

if __name__ == '__main__':
    unittest.main()
