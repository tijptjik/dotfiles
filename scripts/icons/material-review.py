#!/usr/bin/env python3
"""Rebuild the camera-led before/after review from frozen pre-pass SVGs."""
import hashlib
import json
from html import escape
from pathlib import Path

from gallery import sheet
from material_art import ART, DETAILS

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / '.local/icon-reviews/docs/assets/icon-material-review'
THEME = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
FEATURED = ['camera', 'cheese', 'bottles', 'disks', 'files', 'obsidian',
            'monochrome-music', 'file-roller', 'clocks', 'maps', 'software', 'weather',
            'snapraid', 'llmtrim', 'contacts', 'document-scanner', 'vlc', 'tippecanoe']


def main():
    from review_paths import prepare_review
    prepare_review(ROOT)
    catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
    featured = [k for k in FEATURED if k in catalog]
    latest_batch = max(v.get('review_batch', 0) for v in catalog.values())
    revised = [k for k,v in catalog.items() if v.get('review_batch') == latest_batch]
    keys = revised + [k for k in featured if k not in revised] + sorted(set(catalog) - set(featured) - set(revised), key=lambda k: catalog[k]['name'].casefold())
    cards, manifest = [], {}
    for key in keys:
        name = catalog[key]['name']
        batch = catalog[key].get('review_batch', 0)
        before_folder = {4: 'revision-1', 5: 'revision-2', 6: 'revision-3', 7: 'revision-4', 8: 'revision-5', 9: 'revision-6', 10: 'revision-7', 11: 'revision-8', 12: 'revision-9', 13: 'revision-10', 14: 'revision-11', 15: 'revision-12', 16: 'revision-13', 17: 'revision-14', 18: 'revision-15', 19: 'revision-16', 20: 'revision-17'}.get(batch, 'before')
        before = ASSETS / before_folder / f'{key}.svg'
        after = THEME / f'{key}.svg'
        kind = 'Reference artwork · frameless' if key == 'camera' else ('Clean filled artwork' if batch >= 4 else 'Object illustration' if key in ART else ('Material details' if key in DETAILS else 'Pigment & shading'))
        introduced = catalog[key].get('introduced_batch') == batch
        if introduced:
            kind = 'New identity'
        manifest[key] = {'before_folder': None if introduced else before_folder,
                         'before_sha256': None if introduced else hashlib.sha256(before.read_bytes()).hexdigest(),
                         'after_sha256': hashlib.sha256(after.read_bytes()).hexdigest(), 'treatment': kind}
        before_figure = ('<figure><figcaption>New identity · no previous artwork</figcaption></figure>' if introduced else
                         f'<figure><img src="assets/icon-material-review/{before_folder}/{key}.svg" alt="{escape(name)} before"><figcaption>Before</figcaption></figure>')
        cards.append(f'''<article data-name="{escape(name.casefold())}"><h2>{escape(name)}</h2><p class="kind">{kind}</p><div class="pair">
{before_figure}
<figure><img src="../home/dot_local/share/icons/rose-punk/scalable/apps/{key}.svg" alt="{escape(name)} reworked"><figcaption>{'Reference' if key == 'camera' else 'Reworked'}</figcaption></figure></div></article>''')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rose Punk · The camera study</title><style>
:root{color-scheme:dark;--icon-size:96px}*{box-sizing:border-box}body{margin:0;background:#191724;color:#eee9e6;font:15px/1.55 system-ui}header{padding:48px max(24px,5vw) 30px;max-width:1100px}header img{float:right;width:144px;height:144px;margin:0 0 20px 24px}h1{font-size:clamp(30px,4vw,48px);line-height:1.1;font-weight:550;margin:10px 0 20px}header p{max-width:710px;color:#bbb5c9}.eyebrow{color:#e6ae62;font-size:12px;letter-spacing:.16em;text-transform:uppercase}nav{position:sticky;top:0;z-index:1;background:#191724f5;border-block:1px solid #393348;padding:16px max(24px,5vw);display:flex;gap:20px;align-items:center;flex-wrap:wrap}input,select{font:inherit;background:#26233a;color:#eee9e6;border:1px solid #665875;border-radius:7px;padding:8px 12px}label{display:flex;gap:8px;align-items:center}input{max-width:100%}a{color:#9ccfd8}main{padding:24px max(24px,5vw);display:grid;grid-template-columns:repeat(auto-fill,minmax(275px,1fr));gap:16px}article{background:#201c2d;border:1px solid #393348;border-radius:14px;padding:20px}h2{font-size:16px;font-weight:550;margin:0}.kind{font-size:12px;color:#a49bae;margin:4px 0 18px}.pair{display:grid;grid-template-columns:1fr 1fr;align-items:center;gap:10px}figure{margin:0;text-align:center}figure img{width:var(--icon-size);height:var(--icon-size);max-width:100%;object-fit:contain}figcaption{margin-top:8px;font-size:11px;color:#aaa1b5}figure:last-child figcaption{color:#d2bd9f}article[hidden]{display:none}footer{padding:24px max(24px,5vw);color:#aaa1b5}#count{font-size:12px;color:#b3a9bf}@media(max-width:520px){header img{width:88px;height:88px}nav{gap:12px}main{grid-template-columns:1fr}}
</style><header><img src="assets/icon-material-review/before/camera.svg" alt="Camera, the unchanged style reference"><div class="eyebrow">Rose Punk / Material study 01</div><h1>The camera sets the tone.</h1><p>Small objects with a little life: textured grips, folded paper, translucent glass and warm metal. Amber, jade, coral and indigo bring a wider science-fiction palette to the primary frameless set.</p><p>118 icons, with the camera artwork retained as the reference and enlarged for the frameless set. Clean filled forms replace decorative glints and bevels. Retired apps are excluded from this active review.</p></header>
<nav><input id="search" type="search" aria-label="Find an icon" placeholder="Find an icon…"><label>Preview <select id="size" aria-label="Icon size"><option>24</option><option>32</option><option>48</option><option>64</option><option selected>96</option><option>128</option></select> px</label><span id="count">118 icons</span><a href="rose-punk-icons-gallery.html">Full gallery</a></nav><main>'''+''.join(cards)+'''</main><footer>Editable SVG artwork · <a href="rose-punk-icon-style-prompt.md">Style guide</a> · <a href="assets/icon-material-review/manifest.json">Snapshot hashes and treatments</a></footer>
<script>const cards=[...document.querySelectorAll('article')];document.querySelector('#search').addEventListener('input',e=>{let count=0;for(const card of cards){card.hidden=!card.dataset.name.includes(e.target.value.toLowerCase());if(!card.hidden)count++;}document.querySelector('#count').textContent=count+' icons';});document.querySelector('#size').addEventListener('change',e=>document.documentElement.style.setProperty('--icon-size',e.target.value+'px'));</script></html>'''
    html = html.replace('118 icons', f'{len(catalog)} icons').replace('Material study 01', 'Material study 18')
    html = html.replace('</nav>', '<a href="rose-punk-homepage-review.html">Homepage study</a> · <a href="rose-punk-coherence-review.html">Coherence review</a><a href="rose-punk-icons-frameless.html">Primary frameless set</a></nav>')
    (ROOT / '.local/icon-reviews/docs/rose-punk-material-review.html').write_text(html)
    (ROOT / '.local/icon-reviews/docs/rose-punk-refinements.svg').write_text(sheet(revised, catalog, 'Rose Punk / Zed Nightly restored'))
    (ASSETS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (ROOT / '.local/icon-reviews/docs/rose-punk-material-study.svg').write_text(sheet(featured, catalog, 'Rose Punk / The camera study'))
    print(f'Wrote material review: {len(keys)} icons; {len(set(ART) & set(catalog))} illustrations, {len(set(DETAILS) & set(catalog))} detail passes')


if __name__ == '__main__':
    main()
