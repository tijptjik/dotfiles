"""Keep the review's originals distinct from generated Rose Punk artwork."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReviewImages(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.sources = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img':
            self.sources.append(attrs['src'])


@unittest.skipUnless((ROOT / '.local/icon-reviews/docs/rose-punk-color-review.html').is_file(), 'Optional local review archive is absent')
class OriginalIconReviewTests(unittest.TestCase):
    def test_review_has_no_retired_shape_selection_controls(self):
        html = (ROOT / '.local/icon-reviews/docs/rose-punk-color-review.html').read_text()
        for retired in ('id="shapes"', 'href="#shapes"', 'id="export"',
                        'Choose the silhouette', 'rose-punk-shapes-v1'):
            self.assertNotIn(retired, html)
        for retained in ('id="apps"', 'id="search"', 'id="size"', 'id="before"'):
            self.assertIn(retained, html)

    def test_originals_have_intact_sources_and_never_use_generated_baseline(self):
        folder = ROOT / '.local/icon-reviews/docs/assets/icon-review/originals'
        manifest = json.loads((folder / 'manifest.json').read_text())
        catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
        self.assertEqual(set(manifest), set(catalog))
        html = (ROOT / '.local/icon-reviews/docs/rose-punk-color-review.html').read_text()
        sources = ReviewImages(html).sources
        self.assertFalse(any('/baseline/' in path for path in sources))
        generated = {
            hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in ('.local/icon-reviews/docs/assets/icon-review/baseline',
                              '.local/icon-reviews/docs/assets/icon-review/apps')
            for path in (ROOT / directory).glob('*.svg')
        }
        for key, entry in manifest.items():
            with self.subTest(icon=key):
                if 'file' not in entry:
                    self.assertEqual(entry['status'], 'unavailable')
                    continue
                digest = hashlib.sha256((folder / entry['file']).read_bytes()).hexdigest()
                self.assertEqual(digest, entry['sha256'])
                self.assertNotIn(digest, generated)
                self.assertIn('assets/icon-review/originals/' + entry['file'], sources)
                self.assertNotIn('scripts/icons/local/', entry['source'])
                self.assertNotIn('rose-punk', entry['source'])


if __name__ == '__main__':
    unittest.main()
