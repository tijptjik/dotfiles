"""Generated MIME associations stay outside Chezmoi capture."""

import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import tjikup_support
import fleet_capture


REPO = Path(__file__).resolve().parents[1]
CACHE_SOURCE = Path("home/dot_local/share/applications/mimeinfo.cache")
CACHE_TARGET = Path(".local/share/applications/mimeinfo.cache")


class MimeinfoCaptureTests(unittest.TestCase):
    def test_discovered_propagators_have_managed_sources(self):
        for propagator in fleet_capture.discover_propagators():
            with self.subTest(propagator=propagator.name):
                self.assertTrue((REPO / propagator.source).is_file())
                self.assertNotEqual(propagator.target, CACHE_TARGET)

    def test_capture_without_cache_source_leaves_generated_cache_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            home = root / "home"
            target = home / CACHE_TARGET
            target.parent.mkdir(parents=True)
            live = b"[MIME Cache]\ntext/plain=new.desktop;other.desktop;\n"
            for propagator in fleet_capture.discover_propagators():
                source = REPO / propagator.source
                if source.is_file():
                    destination = repo / propagator.source
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)

            for cache_exists in (True, False):
                if cache_exists:
                    target.write_bytes(live)
                else:
                    target.unlink()
                for dry_run in (True, False):
                    with self.subTest(cache_exists=cache_exists, dry_run=dry_run), \
                            patch.object(Path, "home", return_value=home), \
                            contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(fleet_capture.capture(repo, dry_run=dry_run), 0)
                        self.assertFalse((repo / CACHE_SOURCE).exists())
                        self.assertEqual(target.exists(), cache_exists)
                        if cache_exists:
                            self.assertEqual(target.read_bytes(), live)


if __name__ == "__main__":
    unittest.main()
