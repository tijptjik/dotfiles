"""Local hyperlink routing never treats a clicked URL as a shell command."""
import importlib.util
import os
from pathlib import Path
import re
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'native/home/files/.config/herdr/plugins/local/local-files'
spec = importlib.util.spec_from_file_location('herdr_local_files', PLUGIN / 'open_file.py')
opener = importlib.util.module_from_spec(spec)
spec.loader.exec_module(opener)


class FileLinkTests(unittest.TestCase):
    def test_clicked_report_opens_in_existing_file_viewer_on_originating_pane(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'private report $(never execute).json'
            report.write_text('{"tasks": []}')
            for url in (report.as_uri(), report.as_uri().replace('file:///', 'file://localhost/')):
                with self.subTest(url=url), patch.dict(os.environ, {
                        'HERDR_BIN_PATH': '/usr/bin/herdr', 'HERDR_PANE_ID': 'w1:p2'}), \
                        patch.object(opener.subprocess, 'run') as run:
                    opener.open_file(url)
                    command = run.call_args.args[0]
                    self.assertIn(f'HERDR_FILE_VIEWER_OPEN={report}', command)
                    self.assertEqual(command[-2:], ['--target-pane', 'w1:p2'])
                    self.assertIn('herdr-file-viewer', command)
                    self.assertEqual(run.call_args.kwargs, {'check': True})

    def test_remote_urls_missing_files_and_control_characters_do_not_launch(self):
        for url in ('https://example.com', 'file://si/tmp/timings.json', '',
                    'file:///tmp/missing-tjikup-report.json', 'file:///tmp/report%0a.json',
                    'file:///tmp/report.json?command=bad', 'file:///tmp/report.json#fragment'):
            with self.subTest(url=url), patch.object(opener.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    opener.open_file(url)
                run.assert_not_called()

    def test_manifest_only_intercepts_local_file_urls(self):
        manifest = tomllib.loads((PLUGIN / 'herdr-plugin.toml').read_text())
        handler = manifest['link_handlers'][0]
        self.assertEqual(handler['action'], manifest['actions'][0]['id'])
        for url, matched in [('file:///tmp/a', True), ('file://localhost/tmp/a', True),
                             ('file://si/tmp/a', False), ('https://example.com', False)]:
            self.assertEqual(bool(re.search(handler['pattern'], url)), matched)


if __name__ == '__main__':
    unittest.main()
