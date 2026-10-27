#!/usr/bin/env python3
"""Render the Homepage refinement review against frozen pre-pass SVGs."""
import hashlib
from html import escape
import importlib.util
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / '.local/icon-reviews/docs/assets/icon-homepage-coherence-review'
CURRENT = ROOT / 'home/dockers/homepage/images/rose-punk'
spec = importlib.util.spec_from_file_location('homepage_render', Path(__file__).with_name('frameless.py'))
sizing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sizing)
CHANGED = ['seerr', 'profilarr', 'radarr', 'sonarr', 'scrutiny']


def font(size):
    path = subprocess.check_output(['fc-match', 'sans', '-f', '%{file}'], text=True)
    return ImageFont.truetype(path, size)


def paste_icon(canvas, path, x, y, size):
    icon = sizing.render(path.read_text(), size)
    canvas.paste(icon, (x, y), icon)


def main():
    from review_paths import prepare_review
    prepare_review(ROOT)
    catalog = json.loads((ROOT / 'scripts/icons/homepage.json').read_text())
    manifest, cards = {}, []
    for key in CHANGED:
        before, after = ASSETS / 'before' / f'{key}.svg', CURRENT / f'{key}.svg'
        entry = catalog[key]
        manifest[key] = {
            'before_sha256': hashlib.sha256(before.read_bytes()).hexdigest(),
            'after_sha256': hashlib.sha256(after.read_bytes()).hexdigest(),
            'source_sha256': entry['sha256'], 'critique': entry['design_note']}
        before_url = f'assets/icon-homepage-coherence-review/before/{key}.svg'
        after_url = f'../home/dockers/homepage/images/rose-punk/{key}.svg'
        cards.append(f'<article><h2>{escape(entry["name"])}</h2><div class="pair">'
                     f'<figure><img src="{before_url}" alt="Previous {entry["name"]}"><figcaption>Before</figcaption></figure>'
                     f'<figure><img src="{after_url}" alt="Refined {entry["name"]}"><figcaption>Refined</figcaption></figure></div>'
                     f'<p>{escape(entry["design_note"])}</p><div class="sizes">' + ''.join(
                         f'<img src="{after_url}" width="{size}" height="{size}" alt="{entry["name"]} at {size} px">'
                         for size in (24, 32, 48)) + '</div></article>')
    for light in (False, True):
        surface, ink = ('#f0ebe5', '#30283b') if light else ('#191724', '#eee9e6')
        poster = Image.new('RGB', (1120, 940), surface)
        draw = ImageDraw.Draw(poster)
        draw.text((28, 20), 'Rose Punk / Homepage · Refined frameless set', fill=ink, font=font(23))
        draw.text((28, 56), '96 px with 24 / 32 / 48 px previews · Final artwork review', fill=ink, font=font(14))
        for i, (key, entry) in enumerate(catalog.items()):
            x, y = 20 + i % 4 * 275, 96 + i // 4 * 210
            path = CURRENT / f'{key}.svg'
            draw.text((x + 12, y + 4), entry['name'], fill=ink, font=font(15))
            paste_icon(poster, path, x + 80, y + 34, 96)
            for dx, size in ((50, 24), (108, 32), (174, 48)):
                paste_icon(poster, path, x + dx, y + 153 - size // 2, size)
        poster.save(ASSETS / ('current-light.png' if light else 'current.png'))
    comparison = Image.new('RGB', (920, 970), '#201c2d')
    draw = ImageDraw.Draw(comparison)
    draw.text((24, 20), 'Homepage refinements', fill='#eee9e6', font=font(24))
    for x, title in ((210, 'Before'), (370, 'Refined'), (555, '24 / 32 / 48 px')):
        draw.text((x, 65), title, fill='#bbb3cb', font=font(14))
    for i, key in enumerate(CHANGED):
        y = 110 + i * 170
        draw.text((24, y + 36), catalog[key]['name'], fill='#eee9e6', font=font(16))
        paste_icon(comparison, ASSETS / 'before' / f'{key}.svg', 190, y, 96)
        paste_icon(comparison, CURRENT / f'{key}.svg', 350, y, 96)
        for x, size in ((560, 24), (632, 32), (720, 48)):
            paste_icon(comparison, CURRENT / f'{key}.svg', x, y + 48 - size // 2, size)
    comparison.save(ASSETS / 'before-after.png')
    (ASSETS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rose Punk · Homepage coherence review</title><style>
*{box-sizing:border-box}body{margin:0;background:#191724;color:#eee9e6;font:15px/1.6 system-ui}header,main{padding:28px 4vw}header{max-width:1000px}h1{font-weight:550;line-height:1.2}p{color:#bbb3cb}a{color:#9ccfd8}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}article{padding:22px;background:#201c2d;border:1px solid #393348;border-radius:14px}h2{font-size:17px}.pair{display:flex;justify-content:space-evenly;gap:24px}figure{margin:0;text-align:center}.pair img{width:96px;height:96px}figcaption{color:#bbb3cb;font-size:12px}.sizes{display:flex;align-items:center;justify-content:center;gap:28px;min-height:56px}</style>
<header><h1>Calmer detail, clearer small icons.</h1><p>The palette and object language already belong together. This pass replaces Seerr's scratch-like fibres with continuous pigment bands, gives Profilarr natural face proportions and shaped shoulders, clarifies the paired radar screens, and brings Scrutiny into the book-and-ribbon rose family.</p>
<p>Tautulli stays deliberately simple; the shared desktop identities and the remaining service illustrations are retained. At 24 px, Profilarr reads as a group and secondary material details recede. Pale unbacked marks remain best suited to dark surfaces.</p>
<p><a href="assets/icon-homepage-coherence-review/current.png">Whole set</a> · <a href="assets/icon-homepage-coherence-review/current-light.png">Light background check</a> · <a href="assets/icon-homepage-coherence-review/before-after.png">Before / after image</a> · <a href="rose-punk-homepage-review.html">Compare with original app icons</a></p>
<p>Prepared locally for visual approval. Final frameless sign-off and Rose Punk Framed generation remain pending.</p></header><main>CARDS</main></html>'''
    (ROOT / '.local/icon-reviews/docs/rose-punk-homepage-coherence-review.html').write_text(html.replace('CARDS', ''.join(cards)))
    print(f'Rendered {len(catalog)} Homepage icons on two backgrounds and {len(CHANGED)} before/after comparisons')


if __name__ == '__main__':
    main()
