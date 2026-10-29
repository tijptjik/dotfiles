#!/usr/bin/env python3
"""Build local utilities from the HTML served by the pinned viewer image.

Usage: build_css.py viewer.html tailwind-9.5.0.css
Fetch viewer.html from the local viewer, without logging into it. The existing
inline custom CSS remains in the document; this builds Tailwind utilities only.
Requires Node/npm. Tailwind is pinned to the version bundled by image 9.5.0.
"""
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    source, output = map(Path, sys.argv[1:])
    html = source.read_text()
    marker = 'tailwind.config = '
    if html.count(marker) != 1:
        raise SystemExit('Expected exactly one inline Tailwind configuration')
    config = html.split(marker, 1)[1].split('</script>', 1)[0].strip().rstrip(';')
    with tempfile.TemporaryDirectory(prefix='tga-css-') as directory:
        root = Path(directory)
        (root / 'viewer.html').write_text(html)
        (root / 'tailwind.config.cjs').write_text(
            'module.exports = ' + config + ';\nmodule.exports.content = ["./viewer.html"];\n')
        (root / 'input.css').write_text('@tailwind base;\n@tailwind components;\n@tailwind utilities;\n')
        subprocess.run(['npx', '--yes', '--package', 'tailwindcss@3.4.17', 'tailwindcss',
                        '-c', 'tailwind.config.cjs', '-i', 'input.css',
                        '-o', str(output.resolve()), '--minify'], cwd=root, check=True)


if __name__ == '__main__':
    main()
