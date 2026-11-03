#!/usr/bin/env python3
"""Review Craft app originals and Rose Punk at five sizes on four surfaces.

Optional unmodified reference images live in the ignored review directory.
Missing references are labelled, never replaced with themed artwork. This
command is offline and does not record artwork approval or build framed icons.
"""
import hashlib
import json
from html import escape
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from frameless import render
from icon_data import HERE, PRIMARY, REVIEWS, write_file

SIZES = (24, 32, 48, 64, 96)
SURFACES = {'dark': '#191724', 'plum': '#34304f',
            'ivory': '#fffaf2', 'white': '#ffffff'}


def main():
    catalog = json.loads((HERE / 'catalog.json').read_text())
    provenance = json.loads((HERE / 'provenance.json').read_text())
    keys = [key for key, entry in catalog.items() if entry.get('suite') == 'artcraft']
    pending = sum(not catalog[key].get('reviewed') for key in keys)
    review_status = f'{pending} icons awaiting review' if pending else 'ArtCraft artwork approved'
    assets = REVIEWS / 'assets/artcraft'
    originals = assets / 'originals'
    assets.mkdir(parents=True, exist_ok=True)
    camera = PRIMARY / 'scalable/apps/camera.svg'
    camera_hash = hashlib.sha256(camera.read_bytes()).hexdigest()
    font = ImageFont.truetype('DejaVuSans.ttf', 15)
    small = ImageFont.truetype('DejaVuSans.ttf', 12)
    heading = ImageFont.truetype('DejaVuSans.ttf', 26)
    current = {key: (PRIMARY / f'scalable/apps/{key}.svg').read_text()
               for key in ['camera', *keys]}
    reference = {}
    manifest = {'camera_sha256': camera_hash,
                'owl_reference_sha256': hashlib.sha256(current['filmcraft'].encode()).hexdigest(),
                'icons': {}}
    for key in keys:
        path = originals / f'{key}.webp'
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != provenance[key]['reference_sha256']:
                raise ValueError(f'Reference hash mismatch: {path}')
            reference[key] = Image.open(path).convert('RGBA')
        manifest['icons'][key] = {
            'reference': provenance[key]['reference'],
            'reference_sha256': provenance[key]['reference_sha256'],
            'reference_available': key in reference,
            'themed_sha256': hashlib.sha256(current[key].encode()).hexdigest(),
            'treatment': provenance[key]['design_note'],
        }

    def paste(canvas, artwork, size, x, y):
        bitmap = render(artwork, size)
        canvas.paste(bitmap, (x, y), bitmap)

    # Actual pixel sizes, one row per app, with camera at the same sizes.
    for name, surface in SURFACES.items():
        ink = '#fff0da' if name in ('dark', 'plum') else '#34304f'
        sheet = Image.new('RGB', (940, 140 + 116 * (len(keys) + 1)), surface)
        draw = ImageDraw.Draw(sheet)
        draw.text((24, 20), f'Rose Punk / ArtCraft / {name}', fill=ink, font=heading)
        draw.text((24, 60), 'Primary frameless candidates · official reference at left · camera unchanged', fill=ink, font=small)
        for size, x in zip(SIZES, (360, 440, 540, 660, 800)):
            draw.text((x, 100), f'{size} px', fill=ink, font=small)
        draw.text((226, 100), 'Official', fill=ink, font=small)
        for row, key in enumerate(['camera', *keys]):
            y = 132 + row * 116
            label = 'Camera reference' if key == 'camera' else catalog[key]['name']
            draw.text((24, y + 38), label, fill=ink, font=font)
            if key in reference:
                original = reference[key].copy()
                original.thumbnail((64, 64), Image.Resampling.LANCZOS)
                sheet.paste(original, (226, y + 16), original)
            elif key != 'camera':
                draw.text((226, y + 38), 'Not cached', fill=ink, font=small)
            for size, x in zip(SIZES, (360, 440, 540, 660, 800)):
                paste(sheet, current[key], size, x, y + (96 - size) // 2)
        sheet.save(REVIEWS / f'rose-punk-artcraft-{name}.png')

    overview = Image.new('RGB', (1200, 180 + ((len(keys) + 4) // 5) * 224), SURFACES['dark'])
    draw = ImageDraw.Draw(overview)
    draw.text((28, 24), 'ArtCraft / Rose Punk', fill='#fff0da', font=heading)
    draw.text((28, 65), f'Official → Rose Punk · owl reference retained · {review_status}', fill='#c4b5db', font=font)
    draw.text((28, 100), 'Studio and Launcher retain their official logo.', fill='#c4b5db', font=small)
    paste(overview, current['camera'], 96, 1000, 16)
    draw.text((991, 118), 'Unchanged camera', fill='#c4b5db', font=small)
    for i, key in enumerate(keys):
        x, y = (i % 5) * 240, 176 + (i // 5) * 224
        draw.text((x + 20, y), catalog[key]['name'], fill='#fff0da', font=font)
        if key in reference:
            original = reference[key].copy()
            original.thumbnail((72, 72), Image.Resampling.LANCZOS)
            overview.paste(original, (x + 16, y + 48), original)
        paste(overview, current[key], 112, x + 108, y + 28)
        draw.text((x + 18, y + 144), 'Official', fill='#c4b5db', font=small)
        draw.text((x + 120, y + 144), 'Rose Punk', fill='#c4b5db', font=small)
        paste(overview, current[key], 24, x + 120, y + 175)
        paste(overview, current[key], 32, x + 164, y + 171)
    overview.save(REVIEWS / 'rose-punk-artcraft-overview.png')

    # A family-only view makes geometry, weight and shading easier to compare.
    for name in ('dark', 'ivory'):
        ink = '#fff0da' if name == 'dark' else '#34304f'
        family = Image.new('RGB', (1100, 850), SURFACES[name])
        draw = ImageDraw.Draw(family)
        draw.text((28, 20), 'Rose Punk / ArtCraft / family refinement', fill=ink, font=heading)
        draw.text((28, 58), 'Owl unchanged · shared curves, shading and detail scale · 24 / 32 px below', fill=ink, font=font)
        paste(family, current['camera'], 64, 986, 12)
        for i, key in enumerate(keys):
            x, y = (i % 5) * 220, 105 + (i // 5) * 245
            paste(family, current[key], 128, x + 46, y)
            draw.text((x + 28, y + 144), catalog[key]['name'], fill=ink, font=font)
            if key == 'filmcraft':
                draw.text((x + 28, y + 166), 'UNCHANGED REFERENCE', fill=ink, font=small)
            paste(family, current[key], 24, x + 58, y + 196)
            paste(family, current[key], 32, x + 112, y + 192)
        family.save(REVIEWS / f'rose-punk-artcraft-family-{name}.png')

    # Frozen pre-refinement art is optional and is never changed by this tool.
    comparisons = (
        ('artcraft-coherence', 'rose-punk-artcraft-coherence.png',
         'ArtCraft / previous Rose Punk → owl-led refinement'),
        ('artcraft-r10', 'rose-punk-artcraft-r10-comparison.png',
         'ArtCraft / critique baseline → geometry revision'),
    )
    for folder, output_name, title in comparisons:
        coherence = REVIEWS / 'assets' / folder
        baseline_path = coherence / 'baseline.json'
        if not baseline_path.exists():
            continue
        baseline = json.loads(baseline_path.read_text())
        comparison = Image.new('RGB', (1200, 100 + 240 * ((len(keys) + 2) // 3)), SURFACES['dark'])
        draw = ImageDraw.Draw(comparison)
        draw.text((28, 20), title, fill='#fff0da', font=heading)
        draw.text((28, 60), 'Equal sizes: 112 px above, 24 / 32 px below · owl unchanged', fill='#c4b5db', font=font)
        for i, key in enumerate(keys):
            previous = (coherence / 'before' / f'{key}.svg').read_text()
            if hashlib.sha256(previous.encode()).hexdigest() != baseline['icons'][key]:
                raise ValueError(f'Frozen comparison changed: {key}')
            x, y = (i % 3) * 400, 104 + (i // 3) * 240
            draw.text((x + 24, y), catalog[key]['name'], fill='#fff0da', font=font)
            for dx, artwork, label in ((28, previous, 'Previous'), (230, current[key], 'Reference' if key == 'filmcraft' else 'Refined')):
                paste(comparison, artwork, 112, x + dx, y + 26)
                draw.text((x + dx, y + 145), label, fill='#c4b5db', font=small)
                paste(comparison, artwork, 24, x + dx + 8, y + 176)
                paste(comparison, artwork, 32, x + dx + 56, y + 172)
        comparison.save(REVIEWS / output_name)

    cards = []
    for key in keys:
        # Theme copy keeps this local review portable inside its ignored folder.
        write_file(assets / f'{key}.svg', current[key].encode())
        original = (f'<img class="original" src="assets/artcraft/originals/{key}.webp" alt="Official {escape(catalog[key]["name"])}">'
                    if key in reference else '<span>Official image not cached</span>')
        cards.append(f'<article><h2>{escape(catalog[key]["name"])}</h2><div>{original}'
                     f'<img class="themed" src="assets/artcraft/{key}.svg" alt="Rose Punk {escape(catalog[key]["name"])}"></div>'
                     f'<p>{escape(provenance[key]["design_note"].split(". ")[0])}</p>'
                     f'<a href="{escape(provenance[key]["reference_page"])}">Official reference</a></article>')
    write_file(assets / 'camera.svg', current['camera'].encode())
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ArtCraft / Rose Punk review</title><style>
*{box-sizing:border-box}body{margin:0;background:#191724;color:#fff0da;font:15px system-ui}header{padding:24px;position:sticky;top:0;background:inherit;border-bottom:1px solid #8885;z-index:1}h1{margin:0 0 10px}header img{float:right;width:64px;height:64px}p{opacity:.8}select{padding:8px;margin:0 20px 0 8px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:20px;padding:24px}article{border:1px solid #8885;border-radius:14px;padding:20px}h2{font-size:18px}article div{height:120px;display:flex;align-items:center;justify-content:space-around;gap:20px}.original{width:80px;height:80px;object-fit:contain}.themed{width:var(--size,96px);height:var(--size,96px)}a{color:inherit}footer{padding:24px}
</style><header><img src="assets/artcraft/camera.svg" alt="Unchanged camera reference"><h1>ArtCraft / Rose Punk</h1><p>Official originals on the left; refined SVGs on the right. Owl reference and camera unchanged. Fourteen refinements await review.</p>
<label>Size<select id="size"><option>24</option><option>32</option><option>48</option><option>64</option><option selected>96</option></select></label>
<label>Surface<select id="surface"><option value="#191724">Dark</option><option value="#34304f">Plum</option><option value="#fffaf2">Ivory</option><option value="#ffffff">White</option></select></label></header><main>'''+''.join(cards)+'''</main><footer>Studio and Launcher retain their official logo. Craft Anything uses an independently drawn raven. No deployment, release or framed approval.</footer>
<script>document.querySelector('#size').onchange=e=>document.documentElement.style.setProperty('--size',e.target.value+'px');document.querySelector('#surface').onchange=e=>{document.body.style.background=e.target.value;document.body.style.color=e.target.value.startsWith('#ff')?'#34304f':'#fff0da';};</script></html>'''
    html = html.replace('Fourteen refinements await review.', review_status + '.')
    write_file(REVIEWS / 'rose-punk-artcraft.html', html.encode())
    write_file(assets / 'manifest.json', (json.dumps(manifest, indent=2)+'\n').encode())
    assert hashlib.sha256(camera.read_bytes()).hexdigest() == camera_hash
    print(REVIEWS / 'rose-punk-artcraft.html')


if __name__ == '__main__':
    main()
