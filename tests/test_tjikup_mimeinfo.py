"""Generated MIME associations are captured before applying dotfiles."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
import fleet_update
from fleet_update.propagators.mimeinfo import PROPAGATOR


class MimeinfoCaptureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.source = self.repo / PROPAGATOR.source
        self.target = self.home / PROPAGATOR.target
        self.source.parent.mkdir(parents=True)
        self.target.parent.mkdir(parents=True)
        self.before = "[MIME Cache]\nx-scheme-handler/obsidian=old.desktop;\n"
        self.live = "[MIME Cache]\ntext/plain=new.desktop;other.desktop;\n"
        self.source.write_text(self.before)
        self.target.write_text(self.live)

    def capture(self, *, dry_run=False):
        with patch.object(fleet_update, "discover_propagators", return_value=[PROPAGATOR]), \
                patch.object(Path, "home", return_value=self.home), \
                contextlib.redirect_stdout(io.StringIO()):
            return fleet_update.capture(self.repo, dry_run=dry_run)

    def test_capture_replaces_stale_associations_and_preserves_live_cache(self):
        self.assertIn(PROPAGATOR, fleet_update.discover_propagators())
        self.assertEqual(self.capture(), 0)
        self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
        self.assertEqual(self.target.read_text(), self.live)
        self.assertEqual(self.capture(), 0)

    def test_dry_run_leaves_source_unchanged(self):
        self.assertEqual(self.capture(dry_run=True), 0)
        self.assertEqual(self.source.read_text(), self.before)

    def test_missing_cache_is_skipped(self):
        self.target.unlink()
        self.assertEqual(self.capture(), 0)
        self.assertEqual(self.source.read_text(), self.before)

    def test_incomplete_cache_does_not_replace_source(self):
        self.target.write_text("")
        self.assertEqual(self.capture(), 1)
        self.assertEqual(self.source.read_text(), self.before)


if __name__ == "__main__":
    unittest.main()
