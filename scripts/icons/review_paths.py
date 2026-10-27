"""Keep optional icon review outputs outside the tracked source tree."""
from pathlib import Path


def prepare_review(root):
    root = Path(root).resolve()
    archive = root / '.local/icon-reviews'
    docs = archive / 'docs'
    docs.mkdir(parents=True, exist_ok=True)
    # Existing gallery URLs remain relative to a docs/ directory. These local
    # links expose the current SVG sources without copying them into snapshots.
    for name in ('home', 'scripts'):
        link = archive / name
        if not link.exists() and not link.is_symlink():
            link.symlink_to(root / name, target_is_directory=True)
    for source in (root / 'docs').glob('rose-punk-*.md'):
        link = docs / source.name
        if link.is_symlink():
            link.unlink()
        # The repository guide points into this archive. Its local copy already
        # lives here, so its gallery links need no archive-directory prefix.
        link.write_text(source.read_text().replace('../.local/icon-reviews/docs/', ''))
    return docs
