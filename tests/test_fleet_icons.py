"""Check decorated terminal rows without changing report or outcome semantics."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
from fleet_update.status import NATIVE_LABELS, decorate_native_row
from fleet_update.icons import HookProgress, title_icon
from fleet_update.presentation import ANSI
from fleet_update.icon_catalog import display_title
from tjikup import runtime


class FleetIconTests(unittest.TestCase):
    def test_empty_section_uses_tjikup_icon_and_exact_message_once(self):
        for icons in ('0', '1'):
            with self.subTest(icons=icons), tempfile.TemporaryDirectory() as directory, \
                    patch.dict(os.environ, {'TJIKUP_ICONS': icons, 'TJIKUP_KITTY_ICONS': '0',
                        'TJIKUP_COLOR': '0', 'TJIKUP_REPORT_FILE': str(Path(directory) / 'report')}), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                progress = HookProgress(section='Home + System Tasks', live=False)
                progress.finish('skip', 'Zed', verb='SKIP')
                progress.finish_empty_section()
                progress.finish_empty_section()
                glyph = title_icon('Tjikup') + ' ' if icons == '1' else ''
                self.assertEqual(output.getvalue(),
                    '\nHome + System Tasks\n\nCHECK   ✓ ' + glyph + 'No changes needed\n')
                self.assertEqual((Path(directory) / 'report').read_text(),
                    'SKIP\t✓\tZed\t\nCHECK\t✓\tTjikup\tNo changes needed\n')

    def test_run_once_rows_have_service_icons_without_recording_again(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
                'TJIKUP_ICONS': '1', 'TJIKUP_KITTY_ICONS': '0', 'TJIKUP_COLOR': '0',
                'TJIKUP_COLUMNS': '100', 'TJIKUP_REPORT_FILE': str(Path(directory) / 'report')}):
            for source, label in NATIVE_LABELS.items():
                with self.subTest(source=source):
                    row = decorate_native_row(runtime.format_status('CONFIG', '✓', source, 'ready'))
                    self.assertIn(title_icon(label) + ' ' + display_title(label), row)
                    self.assertIn('ready', row)
            self.assertFalse((Path(directory) / 'report').exists())

    def setUp(self):
        env = patch.dict(os.environ, {'TJIKUP_KITTY_ICONS': '0'})
        env.start()
        self.addCleanup(env.stop)

    def test_terminal_icons_leave_report_and_outcome_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report"
            with patch.dict(os.environ, {"TJIKUP_ICONS": "1", "TJIKUP_COLOR": "1",
                                        "TJIKUP_COLUMNS": "80", "TJIKUP_REPORT_FILE": str(report)}):
                stream = io.StringIO()
                progress = HookProgress(stream=stream, live=True)
                progress.start("python", "Python (environment)", "SYNC")
                progress.finish("python", "Python (environment)", verb="SYNC", note="no changes")
            self.assertEqual(stream.getvalue().count("\ue73c Python"), 1)
            self.assertNotIn("SKIP", stream.getvalue())
            self.assertNotIn("no changes", stream.getvalue())
            self.assertEqual(progress.height, 0)
            self.assertEqual(progress.rows, {})
            self.assertEqual(report.read_text(), "SKIP\t✓\tPython (environment)\tno changes\n")

    def test_skipped_results_are_silent_without_live_progress(self):
        with patch.dict(os.environ, {'TJIKUP_ICONS': '1'}):
            stream = io.StringIO()
            progress = HookProgress(stream=stream, live=False)
            for verb, icon, note in [('SKIP', '✓', 'no changes'),
                                     ('SKIP', '-', 'not installed'),
                                     ('SYNC', '✓', '2 pkgs; no updates')]:
                progress.finish('capture', 'Zed', verb=verb, icon=icon, note=note, record=False)
            self.assertEqual(stream.getvalue(), '')
            for verb, icon in [('SYNC', '✓'), ('WARN', '!'), ('FAILED', '✗')]:
                progress.finish('capture', 'Zed', verb=verb, icon=icon, note='details', record=False)
                self.assertIn(verb, stream.getvalue())

    def test_native_skips_are_hidden_even_without_a_known_service_icon(self):
        for label in ('Bitwarden CLIs', 'Unknown service'):
            for verb, note in [('SKIP', 'available'), ('SYNC', 'no changes')]:
                with self.subTest(label=label, verb=verb):
                    row = runtime.format_status(verb, '✓', label, note)
                    self.assertEqual(decorate_native_row(row), '')
                    self.assertEqual(decorate_native_row('\r\033[2K' + row), '\033[2K')

    def test_plain_and_disabled_output_have_no_title_icons(self):
        cases = [{"TJIKUP_COLOR": "0", "TERM": "xterm"},
                 {"TJIKUP_COLOR": "1", "TERM": "dumb"},
                 {"TJIKUP_COLOR": "1", "TERM": "xterm", "TJIKUP_ICONS": "0"}]
        for env in cases:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                stream = io.StringIO()
                HookProgress(stream=stream, live=False).finish("rust", "Rust (packages)", record=False)
                self.assertIn("✓ Rust (Packages)", ANSI.sub("", stream.getvalue()))

    def test_coloured_forwarded_rows_have_icons_and_fit_narrow_width(self):
        with patch.dict(os.environ, {"TERM": "xterm", "TJIKUP_COLOR": "1", "TJIKUP_COLUMNS": "40"}, clear=True):
            stream = io.StringIO()
            HookProgress(stream=stream, live=False).finish(
                "fonts", "Assets (fonts)", note="updated", record=False)
            row = ANSI.sub("", stream.getvalue()).rstrip("\n")
            self.assertIn("✓ \uf031 Assets", row)
            self.assertLessEqual(runtime.display_width(row), 39)

    def test_asset_subtypes_and_unknown_services(self):
        self.assertNotEqual(title_icon("Assets (fonts)"), title_icon("Assets (icon cache)"))
        self.assertEqual(title_icon("Fedora (repositories)"), title_icon("Fedora (release)"))
        self.assertEqual(title_icon("New service"), "\uf013")
        for label in ("Google Chrome stable", "Sublime Text", "Obsidian", "Greetjik", "Gitfetch", "GDM"):
            with self.subTest(label=label):
                self.assertNotEqual(title_icon(label), title_icon("New service"))

    def test_native_rows_share_icons_without_duplicate_report_events(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
                'TJIKUP_ICONS': '1', 'TJIKUP_COLOR': '1', 'TERM': 'xterm',
                'TJIKUP_COLUMNS': '100', 'TJIKUP_REPORT_FILE': str(Path(directory) / 'report')}):
            for source, expected in [('Bitwarden CLIs', 'Bitwarden (CLIs)'),
                                     ('Assets (user fonts)', 'Assets (font folder migration)')]:
                row = decorate_native_row(runtime.format_status('UPDATE', '✓', source, 'available'))
                self.assertIn(title_icon(expected) + ' ', row)
                self.assertIn(expected.partition(' (')[0], ANSI.sub('', row))
            self.assertFalse((Path(directory) / 'report').exists())
            pending = 'UPDATE  ... Bitwarden CLIs'
            self.assertEqual(decorate_native_row(pending), pending)

    def test_display_titles_preserve_brands_acronyms_and_source_identity(self):
        cases = {
            'llmtrim (Herdr plugin)': 'Llmtrim (Herdr Plugin)',
            'Assets (Rose Punk icons)': 'Assets (Rose Punk Icons)',
            'Assets (icon cache)': 'Assets (Icon Cache)',
            'Fedora (COPR repositories)': 'Fedora (COPR Repositories)',
            'Fedora (RPM packages)': 'Fedora (RPM Packages)',
            'Google Chrome stable': 'Google Chrome Stable',
            'Gtk-bookmarks': 'GTK Bookmarks',
            'Zapzap': 'ZapZap',
            'Mullvad (LAN)': 'Mullvad (LAN)',
            'Chezetc (system)': 'Chezetc (System)',
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(display_title(source), expected)
        self.assertEqual(display_title('/private/path with spaces'), '/private/path with spaces')

    def test_prerequisite_capture_and_repository_labels_have_explicit_sprites(self):
        import json
        sprites = json.loads((Path(__file__).resolve().parents[1] /
                              'scripts/fleet_update/icons32.json').read_text())['sprites']
        labels = ('Bitwarden', 'Chezmoi', 'Fish', 'UV', 'FNM', 'Gum', 'Bun',
                  'Zed', 'Herdr', 'Solaar', 'Fcitx', 'Codex', 'Zapzap',
                  'Gtk-bookmarks', 'Local Changes', 'dotjik', 'systjik', 'tjikos', 'GDM')
        for label in labels:
            with self.subTest(label=label):
                self.assertIn(label, sprites)
                self.assertNotEqual(sprites[label], sprites['*'])


if __name__ == "__main__":
    unittest.main()
