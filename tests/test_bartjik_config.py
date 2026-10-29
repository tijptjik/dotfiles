import native_render
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'native/home/files/.config/bartjik/config.json.j2'


@unittest.skipUnless(shutil.which('render-native'), 'Native renderer required')
class BartjikConfigTests(unittest.TestCase):
    def render(self, host):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'render-native.json'
            config.write_text(json.dumps({'data': {'isLaptop': host == 'li'}}))
            return json.loads(subprocess.check_output([
                'render-native', '--config', str(config), '--source', str(root),
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

    def test_laptop_compact_modules(self):
        left, right = self.render('li')['bars']
        self.assertEqual(left['islands'][0], {
            'id': 'applications', 'modules': ['tray'],
        })
        modules = [module for bar in (left, right)
                   for island in bar['islands'] for module in island['modules']]
        self.assertEqual(modules.count('tray'), 1)
        self.assertNotIn('prices', modules)
        self.assertNotIn('credit', modules)
        ai = next(island for island in right['islands'] if island['id'] == 'ai')
        self.assertEqual(ai['modules'], ['quota'])

    def test_desktop_modules_unchanged(self):
        for host in ('fi', 'si'):
            with self.subTest(host=host):
                left, right = self.render(host)['bars']
                self.assertEqual(left['islands'][0]['modules'], ['prices'])
                self.assertEqual(right['islands'][0]['modules'], ['tray'])
                self.assertEqual(right['islands'][1]['modules'], ['quota', 'credit'])
