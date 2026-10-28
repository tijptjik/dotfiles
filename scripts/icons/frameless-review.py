#!/usr/bin/env python3
"""Export the primary frameless icons and compare them with historical framed art.

Rendering measurements require PyGObject/librsvg, pycairo and Pillow. Output
remains editable SVG; rasterization only measures coverage and renders previews.
"""
import hashlib
import importlib.util
from html import escape
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
from icon_data import gallery_catalog, write_tree

# Keep these helpers available to existing review consumers loaded by file path.
_spec = importlib.util.spec_from_file_location('icon_sizing', Path(__file__).with_name('frameless.py'))
_sizing = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sizing)
MEASURE_SIZE, normalize, render = _sizing.MEASURE_SIZE, _sizing.normalize, _sizing.render

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / 'native/home/files/.local/share/icons/rose-punk/scalable/apps'
ASSETS = ROOT / '.local/icon-reviews/docs/assets/icon-frameless-review'
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
FEATURED = ['camera', 'firefox', 'files', 'kitty', 'obsidian', 'telegram',
            'codex', 'chatgpt', 'bartjik', 'notjik', 'tjikup', 'runtjik', 'greetjik',
            'chrome', 'spotify', 'steam', 'weather', 'calendar', 'contacts',
            'python', 'rust', 'docker', 'zed', 'zed-preview', 'zed-nightly', 'prowlarr']


def contact_sheet(keys, catalog, title):
    items = []
    for i, key in enumerate(keys):
        x, y = 32 + i % 6 * 164, 102 + i // 6 * 142
        # Each nested SVG has its own gradient/clip IDs within a unique namespace.
        root = ET.parse(ASSETS / 'frameless' / f'{key}.svg').getroot()
        ids = {n.get('id') for n in root.iter() if n.get('id')}
        for node in root.iter():
            for attr, value in list(node.attrib.items()):
                if attr == 'id':
                    node.set(attr, key + '-' + value)
                else:
                    for ident in ids:
                        value = value.replace(f'url(#{ident})', f'url(#{key}-{ident})')
                        if value == '#' + ident:
                            value = '#' + key + '-' + ident
                    node.set(attr, value)
        root.set('x', str(x + 34))
        root.set('y', str(y))
        root.set('width', '96')
        root.set('height', '96')
        items.append(ET.tostring(root, encoding='unicode'))
        items.append(f'<text x="{x + 82}" y="{y + 120}" text-anchor="middle" fill="#c4bdd1" font-size="12">{escape(catalog[key]["name"])}</text>')
    height = 112 + math.ceil(len(keys) / 6) * 142
    return f'<svg xmlns="{SVG}" width="1048" height="{height}" viewBox="0 0 1048 {height}"><rect width="1048" height="{height}" fill="#191724"/><g font-family="sans-serif"><text x="36" y="44" fill="#eee9e6" font-size="26">{escape(title)}</text><text x="36" y="72" fill="#b8aec7" font-size="13">Rose Punk · Primary frameless set · 64 × 64 SVGs · Balanced visible artwork</text>{"".join(items)}</g></svg>'


def review_page(keys, catalog):
    cards = []
    for key in keys:
        name = escape(catalog[key]['name'])
        before = (f'<img loading="lazy" src="assets/icon-frameless-review/framed/{key}.svg" alt="{name}, historical framed icon">'
                  if (ASSETS / 'framed' / f'{key}.svg').is_file() else '<span>No historical version</span>')
        cards.append(f'''<article data-name="{escape(catalog[key]['name'].casefold())}" data-key="{key}"><div class="pair">
<figure class="before">{before}<figcaption>Historical framed</figcaption></figure>
<figure><img loading="lazy" src="assets/icon-frameless-review/frameless/{key}.svg" alt="{name}, enlarged frameless icon"><figcaption>Frameless</figcaption></figure></div><h2>{name}</h2></article>''')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rose Punk · Primary frameless set</title><style>
:root{color-scheme:dark;--size:128px;--surface:#26233a;--ink:#eee9e6;--muted:#b8aec7}*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--ink);font:15px/1.5 system-ui}header{padding:36px 4vw 24px;max-width:1000px}h1{font-size:clamp(28px,4vw,44px);font-weight:550;line-height:1.1;margin:8px 0 18px}header p{color:var(--muted);max-width:760px}.eyebrow{color:#e6ae62;font-size:12px;letter-spacing:.15em;text-transform:uppercase}nav{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:16px 4vw;position:sticky;top:0;z-index:1;background:var(--surface);border-block:1px solid #79708455}input,select{font:inherit;color:var(--ink);background:var(--surface);border:1px solid #797084;border-radius:6px;padding:7px;max-width:100%}label{display:flex;align-items:center;gap:8px}main{padding:28px 4vw;display:grid;grid-template-columns:repeat(auto-fill,minmax(max(230px,calc(var(--size)*2 + 40px)),1fr));gap:24px 8px}article{text-align:center;padding:16px 4px}article[hidden]{display:none}.pair{display:flex;align-items:center;justify-content:center;gap:20px}figure{margin:0}img{width:var(--size);height:var(--size);display:block}figcaption{font-size:11px;color:var(--muted);margin-top:9px}h2{font-size:13px;font-weight:500;margin:14px 0 0}.solo .before,.solo figcaption{display:none}.solo main{grid-template-columns:repeat(auto-fill,minmax(max(130px,calc(var(--size) + 28px)),1fr))}.checker main{background-color:#d4cddd;background-image:conic-gradient(#eee8f0 25%,transparent 0 50%,#eee8f0 0 75%,transparent 0);background-size:20px 20px}.checker article{--ink:#30283b;--muted:#51455f;color:var(--ink)}footer{padding:28px 4vw;color:var(--muted)}a{color:#9f9ce8}#count{color:var(--muted);font-size:12px}@media(max-width:540px){nav{gap:10px}main{grid-template-columns:1fr 1fr}.pair{gap:8px}body:not(.solo) main{grid-template-columns:1fr}}
</style><body class="solo"><header><div class="eyebrow">Rose Punk / Primary icon set</div><h1>Let the shapes stand on their own.</h1><p>COUNT icons, with the common plum tile removed and the artwork enlarged. Compact objects and airy marks are balanced on the same canvas, keeping their natural proportions, colours and internal detail.</p><p>Compare at 24–128 px, then try a different background. Circles, borders and backings that belong to the app symbol itself remain part of its identity. Frameless is the primary Rose Punk set. Final artwork approval is pending; Rose Punk Framed will be derived from the signed-off originals. The comparison shows historical framed artwork.</p></header>
<nav><input id="search" type="search" placeholder="Find an icon…" aria-label="Find an icon"><label>Size <select id="size"><option>24</option><option>32</option><option>48</option><option>64</option><option>96</option><option selected>128</option></select> px</label><label>View <select id="view"><option value="compare">Compare</option><option value="solo" selected>Frameless set</option></select></label><label>Background <select id="background"><option value="dark">Dark</option><option value="plum" selected>Plum</option><option value="light">Light</option><option value="checker">Transparency grid</option></select></label><span id="count" aria-live="polite">COUNT icons</span></nav>
<main>CARDS</main><footer><a href="assets/icon-frameless-review/rose-punk-frameless.zip" download>Download the SVG set</a> · <a href="rose-punk-icons-frameless.svg">Contact sheet</a> · <a href="assets/icon-frameless-review/manifest.json">Sizing and source hashes</a> · <a href="rose-punk-homepage-review.html">Homepage study</a> · <a href="rose-punk-coherence-review.html">Coherence review</a></footer><script>
const $=s=>document.querySelector(s),cards=[...document.querySelectorAll('article')];
$('#search').addEventListener('input',e=>{let count=0;for(const card of cards){card.hidden=!card.dataset.name.includes(e.target.value.trim().toLowerCase());if(!card.hidden)count++}$('#count').textContent=count+' icons'});
$('#size').addEventListener('change',e=>document.documentElement.style.setProperty('--size',e.target.value+'px'));
$('#view').addEventListener('change',e=>document.body.classList.toggle('solo',e.target.value==='solo'));
$('#background').addEventListener('change',e=>{const mode=e.target.value,light=mode==='light';document.body.classList.toggle('checker',mode==='checker');for(const [key,value] of Object.entries({'--surface':light?'#f0ebe5':mode==='plum'?'#26233a':'#191724','--ink':light?'#30283b':'#eee9e6','--muted':light?'#66576f':'#b8aec7'}))document.documentElement.style.setProperty(key,value);document.documentElement.style.colorScheme=light?'light':'dark'});
</script></html>'''.replace('COUNT', str(len(keys))).replace('CARDS', ''.join(cards))


def main():
    from review_paths import prepare_review
    prepare_review(ROOT)
    catalog = gallery_catalog(ROOT / 'scripts/icons')
    keys = [k for k in FEATURED if k in catalog]
    keys += sorted(set(catalog) - set(keys), key=lambda k: catalog[k]['name'].casefold())
    for folder in ('framed', 'frameless'):
        (ASSETS / folder).mkdir(parents=True, exist_ok=True)
    manifest = {'primary_theme': 'rose-punk', 'comparison': 'historical framed snapshots',
                'canvas': 64, 'maximum_extent': 56, 'target_alpha_area': 2200,
                'minimum_extent': 50, 'measurement_size': MEASURE_SIZE, 'icons': {}}
    outputs = {}
    for key in keys:
        historical = ASSETS / 'framed' / f'{key}.svg'
        source = historical.read_bytes() if historical.is_file() else None
        # Historical framed snapshots stay frozen; the primary theme is canonical.
        output = (THEME / f'{key}.svg').read_text()
        outputs[f'{key}.svg'] = output.encode()
        bounds = render(output).getchannel('A').getbbox()
        manifest['icons'][key] = {'result_bounds': [round(v * 64 / MEASURE_SIZE, 3) for v in bounds],
                                  'source_sha256': hashlib.sha256(source).hexdigest() if source else None,
                                  'frameless_sha256': hashlib.sha256(output.encode()).hexdigest()}
    write_tree(ASSETS / 'frameless', outputs)
    (ASSETS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (ROOT / '.local/icon-reviews/docs/rose-punk-icons-frameless.html').write_text(review_page(keys, catalog))
    sheet = contact_sheet(keys, catalog, 'Rose Punk / Frameless set')
    (ROOT / '.local/icon-reviews/docs/rose-punk-icons-frameless.svg').write_text(sheet)
    featured = contact_sheet(keys[:24], catalog, 'Rose Punk / Without the tile')
    (ASSETS / 'preview.svg').write_text(featured)
    # Render a sharing preview at the contact sheet's native aspect ratio.
    import cairo
    import gi
    gi.require_version('Rsvg', '2.0')
    from gi.repository import Rsvg
    height = 112 + math.ceil(len(keys[:24]) / 6) * 142
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1048, height)
    viewport = Rsvg.Rectangle()
    viewport.x, viewport.y, viewport.width, viewport.height = 0, 0, 1048, height
    Rsvg.Handle.new_from_data(featured.encode()).render_document(cairo.Context(surface), viewport)
    surface.write_to_png(str(ASSETS / 'preview.png'))
    with zipfile.ZipFile(ASSETS / 'rose-punk-frameless.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for key in keys:
            info = zipfile.ZipInfo(f'rose-punk-frameless/{key}.svg', (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (ASSETS / 'frameless' / f'{key}.svg').read_bytes())
    print(f'Prepared {len(keys)} frameless icons, comparison, contact sheet and ZIP')


if __name__ == '__main__':
    main()
