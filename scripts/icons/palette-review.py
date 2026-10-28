#!/usr/bin/env python3
"""Show the managed theme alongside the original app icons."""
import ast
import hashlib
import json
from html import escape
from pathlib import Path

from palette import load_palette

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / '.local/icon-reviews/docs/assets/icon-review'
THEME = ROOT / 'native/home/files/.local/share/icons/rose-punk/scalable/apps'


def read_mapping(path, name):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(name)


def main():
    from review_paths import prepare_review
    prepare_review(ROOT)
    config, _, ramps, refs, family, _, _ = load_palette()
    catalog = json.loads((HERE / 'catalog.json').read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    for folder in ('apps', 'fleet'):
        (OUT / folder).mkdir(exist_ok=True)

    for key in catalog:
        (OUT / 'apps' / f'{key}.svg').write_bytes((THEME / f'{key}.svg').read_bytes())

    def img(path, alt, cls=''):
        return f'<img class="{cls}" src="{path}" alt="{escape(alt)}" loading="lazy">'

    fleet = read_mapping(ROOT / 'scripts/icons/icon_catalog.py', 'SERVICE_ICONS')
    fleet_sources = read_mapping(HERE / 'fleet.py', 'SOURCES')
    fleet_cards = []
    for label in fleet:
        key = label.lower().replace(' ', '-')
        output = (THEME / f'{fleet_sources[label]}.svg').read_text()
        (OUT / 'fleet' / f'{key}.svg').write_text(output)
        label = 'Greetjik' if label == 'Pony' else label
        status = 'Custom service symbol · Rainbow mane' if label == 'Greetjik' else 'Managed theme icon'
        fleet_cards.append(f'<article class="card" data-search="{escape(label.lower())}">{img(f"assets/icon-review/fleet/{key}.svg", label)}<strong>{escape(label)}</strong><small>{status}</small></article>')

    originals = json.loads((OUT / 'originals/manifest.json').read_text())
    app_cards = []
    for key in sorted(catalog, key=lambda k: catalog[k]['name'].lower()):
        name = catalog[key]['name']
        original = originals.get(key, {})
        new = f'assets/icon-review/apps/{key}.svg'
        if 'file' in original:
            asset = OUT / 'originals' / original['file']
            if hashlib.sha256(asset.read_bytes()).hexdigest() != original['sha256']:
                raise ValueError(f'Original icon changed: {key}')
            old = f"assets/icon-review/originals/{original['file']}"
            source = escape(original['source'], quote=True)
            before = f'<figure class="before" title="{source}">{img(old, "Original " + name, "original-image")}<figcaption>Original</figcaption></figure>'
            caption = original['kind']
        else:
            before = '<figure class="before"><span class="missing-original">No verified<br>original</span><figcaption>Original unavailable</figcaption></figure>'
            caption = 'No verified original available'
        current = f'<figure>{img(new, "Rose Punk " + name)}<figcaption>Rose Punk</figcaption></figure>'
        app_cards.append(f'<article class="card compare" data-search="{escape(name.lower())}"><div class="pair">{before}{current}</div><strong>{escape(name)}</strong><small>{'rainbow mane' if key == 'greetjik' else family(key)} · {caption}</small></article>')
    swatches = ''.join(f'<div class="swatch"><span style="background:{ramp[1]}"></span><strong>{name.title()}</strong><code>{ramp[1]}</code><small>{config["families"][name][1]}</small></div>' for name, ramp in ramps.items())
    brands = []
    for ref in config['brand_refs']:
        key = ref.split('-', 1)[1]
        label = next((s for s in fleet if s.lower() == key), key.title())
        brands.append(f'<a class="brand" href="{refs[ref]["url"]}" target="_blank" rel="noreferrer">{img(f"assets/icon-review/fleet/{key}.svg", label)}<span>{label} ↗</span></a>')

    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rose Punk · Color & icon review</title>
<style>
:root{color-scheme:dark;--size:64px;--bg:#191724;--muted:#b5b0c6;--line:#393348}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#e5e5e5;font:15px/1.5 system-ui,sans-serif}main,header{max-width:1280px;margin:auto;padding:32px}header{padding-top:64px;padding-bottom:24px}.eyebrow{color:#9ccfd8;letter-spacing:.16em;text-transform:uppercase;font-size:12px}h1{font-size:46px;line-height:1.08;letter-spacing:-.04em;max-width:800px;margin:18px 0}h2{font-size:27px;margin:0 0 10px}h3{font-size:21px;margin:0 0 8px}p{color:var(--muted);max-width:780px;margin:0 0 22px}.lede{font-size:18px;max-width:740px}.badge{display:inline-block;border:1px solid #555169;border-radius:30px;padding:4px 12px;margin:6px 8px 0 0;color:#f6c177;font-size:12px}nav{display:flex;gap:20px;flex-wrap:wrap;margin-top:24px}a{color:#9ccfd8;text-decoration:none}a:hover{text-decoration:underline}section{scroll-margin-top:110px}.swatches{display:grid;grid-template-columns:repeat(8,1fr);gap:10px;margin:20px 0 40px}.swatch{padding:14px;background:#1f1d2e;border:1px solid var(--line);border-radius:14px}.swatch span{display:block;height:36px;border-radius:7px;margin-bottom:12px}.swatch strong,.swatch code,.swatch small{display:block}.swatch code{font-size:12px;color:var(--muted)}.swatch small{font-size:11px;color:var(--muted)}.toolbar{position:sticky;top:0;z-index:3;background:#191724f5;border-block:1px solid var(--line);padding:14px 0;display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:28px}input,select,button{background:#26233a;color:#e5e5e5;border:1px solid #555169;border-radius:8px;padding:9px 13px;font:inherit}button{cursor:pointer}button:hover{border-color:#9ccfd8}input{min-width:230px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(138px,1fr));gap:12px;margin:24px 0 56px}.card{border:1px solid var(--line);border-radius:16px;background:#1f1d2e;padding:20px 10px;text-align:center;min-width:0}.card img{width:var(--size);height:var(--size);object-fit:contain;margin:0 auto 12px}.card strong,.card small{display:block}.card strong{font-size:13px}.card small{font-size:11px;color:var(--muted);margin-top:4px}.pair{display:flex;gap:14px;justify-content:center;align-items:center}.compare figure{margin:0;min-width:0}.compare figcaption{font-size:10px;color:var(--muted);margin-bottom:12px}.compare .original-image{background:#f3f3f3;border-radius:6px}.missing-original{display:flex;width:var(--size);height:var(--size);align-items:center;justify-content:center;font-size:10px;color:var(--muted);margin:0 auto 12px}.compare .pair img{max-width:none;flex:none;height:auto;aspect-ratio:1}.appgrid{grid-template-columns:repeat(auto-fill,minmax(max(190px,calc(var(--size)*2 + 40px)),1fr))}.brands{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0 46px}.brand{display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:12px;padding:10px 14px;font-size:13px}.brand img{width:44px;height:44px}footer{border-top:1px solid var(--line);padding:32px 0;color:var(--muted);font-size:12px}[hidden]{display:none!important}.hide-before .before{display:none}.hide-before .compare .pair img{max-width:100%}@media(max-width:800px){header,main{padding:24px}h1{font-size:34px}.swatches{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style><header><div class="eyebrow">Rose Punk / Illustrated / Study 02</div><h1>One family.<br>More recognizable individuals.</h1><p class="lede">A broader color vocabulary from your existing theme, held together by camera-led materials and balanced frameless silhouettes.</p><span class="badge">Review draft</span><span class="badge">8 color families</span><span class="badge">114 existing app icons</span><nav><a href="#palette">Palette</a><a href="#fleet">Fleet set</a><a href="#apps">Full app comparison</a></nav></header><main>
<section id="palette"><h2>Color and materials carry the family.</h2><p>Every symbol color and gradient stop comes from rose-punk.yml. The primary icons have transparent backgrounds; app-specific backings remain. Coordinated pigments describe individual materials; warm highlights and cool undersides provide relief. Fresh mint teal separates green identities from cyan and blue.</p><div class="swatches">''' + swatches + '''</div></section>
<div class="toolbar"><input id="search" placeholder="Find a service or application" aria-label="Find a service or application"><label>Preview <select id="size"><option>24</option><option>32</option><option>48</option><option selected>64</option><option>96</option></select> px</label><label><input type="checkbox" id="before" checked style="min-width:0"> Compare current</label></div>
<section id="fleet"><h2>The service family</h2><p>Recognizable app geometry where available. Local-tool shapes below are proposals using the first reference in each row; choosing another option records your preference for the next drawing pass.</p><div class="grid">''' + ''.join(fleet_cards) + '''</div><h3>Established app marks</h3><p>Downloaded geometry from Simple Icons and Dashboard Icons. Each preview links to its source. Theme colors are applied for comparison; the source files retain their original paint.</p><div class="brands">''' + ''.join(brands) + '''</div></section>
<section id="apps" style="margin-top:48px"><h2>The complete application comparison</h2><p>Current rose / lilac treatment on the left; proposed color family on the right. Originals are shown on a light backing for contrast. Missing originals are marked explicitly. Use 24 or 32 px above to judge recognition at actual UI sizes.</p><div class="grid appgrid">''' + ''.join(app_cards) + '''</div></section><footer>Originals: <a href="assets/icon-review/originals/manifest.json">Sources and SHA-256</a> · Palette: <a href="../native/home/files/.config/vivid/themes/rose-punk.yml">rose-punk.yml</a> · <a href="../scripts/icons/references/manifest.json">Source URLs, licenses and SHA-256</a> · Rebuild: python3 scripts/icons/palette-review.py<br>This review lives in docs/assets/icon-review. It does not replace the managed icon theme.</footer></main>
<script>
document.querySelector('#size').onchange=e=>document.documentElement.style.setProperty('--size',e.target.value+'px');
document.querySelector('#before').onchange=e=>document.body.classList.toggle('hide-before',!e.target.checked);
document.querySelector('#search').oninput=e=>{const q=e.target.value.toLowerCase();for(const n of document.querySelectorAll('[data-search]'))n.hidden=!n.dataset.search.includes(q)};
</script></html>'''
    html = html.replace('<title>', '<link rel="icon" href="data:,"><title>', 1)
    html = html.replace('Review draft', 'Applied globally').replace('114 existing app icons', f'{len(catalog)} app and service icons')
    html = html.replace('Every symbol color and gradient stop comes from rose-punk.yml.', 'Symbol colors start with Rose Punk and extend into amber, copper, jade, turquoise and indigo for the camera-led material pass. Telegram and Codex retain purple identities.')
    html = html.replace('Local-tool shapes below are proposals using the first reference in each row; choosing another option records your preference for the next drawing pass.', 'These previews match the globally applied theme. Greetjik uses a custom Rainbow Dash-inspired mane.')
    html = html.replace('Current rose / lilac treatment on the left; proposed color family on the right.', 'Original app icons on the left, with their source colors and artwork intact; the current Rose Punk theme on the right.')
    html = html.replace('It does not replace the managed icon theme.', 'The theme is deployed through Chezmoi; this page shows its current artwork.')
    html = html.replace('Compare current', 'Show originals')
    html = html.replace('</nav>', '<a href="rose-punk-homepage-review.html">Homepage study</a><a href="rose-punk-icons-frameless.html">Primary frameless set</a></nav>')
    html = html.replace('raised finish', 'camera-led material detail')
    html = html.replace('Applied globally', 'Current source artwork')
    html = html.replace('These previews match the globally applied theme.', 'These previews match the managed theme sources.')
    html = html.replace('Telegram and Codex retain purple identities.', 'Telegram uses ivory wings with blue folds and rose decals.')
    html = html.replace('The theme is deployed through Chezmoi; this page shows its current artwork.', 'This page shows managed theme sources; deployment is separate.')
    (ROOT / '.local/icon-reviews/docs/rose-punk-color-review.html').write_text(html)
    overview = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Rose Punk fleet overview</title>
<style>body{margin:0;padding:36px;background:#191724;color:#e5e5e5;font:14px system-ui}h1{margin:0 0 8px;font-size:30px}p{margin:0 0 28px;color:#9ccfd8}.grid{display:grid;grid-template-columns:repeat(8,1fr);gap:12px}.card{background:#1f1d2e;border:1px solid #393348;border-radius:16px;text-align:center;padding:18px 8px}.card img{width:80px;height:80px;display:block;margin:0 auto 12px}.card strong{font-size:12px;font-weight:400}.card small{display:none}</style>
<h1>Rose Punk / A wider family</h1><p>Primary frameless set · Camera-led materials · Expanded pigment palette</p><div class="grid">'''
    overview += ''.join(fleet_cards).replace('assets/icon-review/', '') + '</div></html>'
    (OUT / 'index.html').write_text(overview)
    print(f'Built {len(catalog)} app comparisons, {len(fleet_cards)} fleet previews.')


if __name__ == '__main__':
    main()
