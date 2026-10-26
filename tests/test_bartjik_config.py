import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'home/dot_config/bartjik/config.json.tmpl'


@unittest.skipUnless(shutil.which('chezmoi'), 'Chezmoi required')
class BartjikConfigTests(unittest.TestCase):
    def render(self, host):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'chezmoi.json'
            config.write_text(json.dumps({'data': {'isLaptop': host == 'li'}}))
            return json.loads(subprocess.check_output([
                'chezmoi', '--config', str(config), '--source', str(root),
                '--persistent-state', str(root / 'state.db'),
                'execute-template', '-f', str(TEMPLATE),
            ], text=True))

    def test_laptop_uses_screen_edges_on_all_monitors(self):
        config = self.render('li')
        self.assertEqual(config['perMonitor'], {})
        for bar, edge in zip(config['bars'], ('l', 'r')):
            self.assertEqual(bar['monitors'], 'all')
            self.assertEqual((bar['position'], bar['alignment']), (edge, edge))
            self.assertEqual(bar.get('perMonitor', {}), {})
            self.assertEqual(bar['screenGutter'], 'edgeOffset')
            self.assertEqual(bar['offsetY'], -24)

    def test_other_hosts_keep_desktop_layout(self):
        for host in ('fi', 'si'):
            with self.subTest(host=host):
                config = self.render(host)
                left, right = config['bars']
                self.assertEqual(left['monitors'], ['DP-1', 'DP-2'])
                self.assertEqual(right['monitors'], ['DP-1'])
                self.assertEqual((left['alignment'], right['alignment']), ('r', 'l'))
                self.assertIn('DP-2', config['perMonitor'])
                self.assertIn('DP-2', left['perMonitor'])
