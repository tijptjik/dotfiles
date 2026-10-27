import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('obsidian_viewer', str(ROOT / 'home/dot_local/bin/executable_obsidian-viewer'))
spec = importlib.util.spec_from_loader(loader.name, loader)
viewer = importlib.util.module_from_spec(spec)
loader.exec_module(viewer)


class ViewerTests(unittest.TestCase):
    def test_style_settings_without_plugins(self):
        css = '''/* @settings
id: minimal-style
settings:
    -
        id: list-spacing
        type: variable-number-slider
        format: em
    -
        id: base
        type: variable-themed-color
        format: hsl-split
    -
        id: checkbox-shape
        type: class-select
        default: checkbox-square
*/
.theme-dark.minimal-dark {color:red}
.checkbox-circle .task-list-item {border-radius:50%}
body:not(.colorful-headings) h1 {color:inherit}
'''
        result = viewer.compile_style(css, {'darkStyle': 'minimal-dark', 'colorfulHeadings': True}, {
            'minimal-style@@list-spacing': 0.115,
            'minimal-style@@base@@dark': '#110F18',
            'minimal-style@@checkbox-shape': 'checkbox-circle',
        })
        self.assertIn('.theme-dark:is(body)', result)
        self.assertIn(':is(body) .task-list-item', result)
        self.assertIn('body:not(:is(body)) h1', result)
        self.assertIn('--list-spacing: 0.115em;', result)
        self.assertIn('--base-h:', result)

    def test_prepare_isolated_and_refreshes_appearance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'main'
            theme = source / 'themes/Minimal'
            theme.mkdir(parents=True)
            (theme / 'theme.css').write_text('body {color:red}')
            (theme / 'manifest.json').write_text('{}')
            (source / 'appearance.json').write_text(json.dumps({'cssTheme': 'Minimal', 'enabledCssSnippets': ['present', 'missing']}))
            (source / 'snippets').mkdir()
            (source / 'snippets/present.css').write_text('h1 {color:red}')
            (source / 'community-plugins.json').write_text('["dataview"]')
            before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
            state = root / 'viewer'
            viewer.prepare(source, state)
            config = state / 'vault/.obsidian'
            self.assertEqual(json.loads((config / 'community-plugins.json').read_text()), [])
            self.assertEqual(json.loads((config / 'core-plugins.json').read_text()), [])
            self.assertFalse((config / 'plugins').exists())
            self.assertEqual(json.loads((config / 'appearance.json').read_text())['enabledCssSnippets'], ['present'])
            viewer.prepare(source, state)
            self.assertEqual(before, {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
