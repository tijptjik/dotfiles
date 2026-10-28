"""Regression checks that never apply dotfiles or contact Git remotes."""

import contextlib

import io

import os

from pathlib import Path

import shutil

import subprocess

import sys

import tempfile

import threading

import unittest

from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "home/dot_local/lib"))

import tjikup_support

import fleet_capture as tjikup

from fleet_capture.core import UpdateError

from fleet_capture.propagators.zed import update_template

class ZedPropagationTests(unittest.TestCase):
    def propagate(self, source_text, target_text):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, output = (root / name for name in ("source", "target", "output"))
            source.write_text(source_text)
            target.write_text(target_text)
            update_template(source, target, output)
            return output.read_text()

    def test_missing_settings_preserved_while_shared_scalar_updates(self):
        source = '''{
  // Settings not yet applied on this host.
  "markdown_preview": {"limit_content_width": false},
  "lsp": {"biome": {"binary": {
    "path": "{{ .chezmoi.homeDir }}/.bun/bin/biome",
    "arguments": ["lsp-proxy"]
  }}},
  "font_size": 14
}'''
        updated = self.propagate(source, '{"lsp": {}, "font_size": 16}')
        self.assertEqual(updated, source.replace('"font_size": 14', '"font_size": 16'))

    def test_incompatible_structure_still_fails(self):
        for target in ('{"setting": null}', '{"setting": false}'):
            with self.subTest(target=target), self.assertRaises(UpdateError):
                self.propagate('{"setting": ["value"]}', target)

    def test_shorter_live_array_preserves_missing_source_entries(self):
        self.assertEqual(
            self.propagate('{"models": ["a", "b"]}', '{"models": ["c"]}'),
            '{"models": ["c", "b"]}',
        )

class PropagationTests(unittest.TestCase):
    def test_later_failure_leaves_all_sources_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "second"
            first.write_text("original first")
            second.write_text("original second")
            good = Mock(source=first, target=first, optional=False)
            good.name = "first"
            good.propagate.side_effect = lambda source, target, output: output.write_text("updated")
            bad = Mock(source=second, target=second, optional=False)
            bad.name = "second"
            bad.propagate.side_effect = UpdateError("invalid configuration")
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ))
                stack.enter_context(patch.object(sys, "argv", ["tjikup"]))
                stack.enter_context(patch.object(tjikup, "discover_propagators", return_value=[good, bad]))
                for name in ("stage_label",):
                    stack.enter_context(patch.object(tjikup, name))
                command = stack.enter_context(patch("subprocess.run"))
                self.assertEqual(tjikup.capture(root), 1)
                command.assert_not_called()
            self.assertEqual(first.read_text(), "original first")
            self.assertEqual(second.read_text(), "original second")

if __name__ == "__main__":
    unittest.main()
