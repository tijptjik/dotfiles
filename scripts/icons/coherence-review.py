#!/usr/bin/env python3
"""Build the annotated whole-set review against frozen pre-pass artwork."""
import hashlib
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / '.local/icon-reviews/docs/assets/icon-coherence-review'
THEME = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
HOMEPAGE = ROOT / 'home/dockers/homepage/images/rose-punk'
NOTES = {
    'spotify': 'Uses Audio Player’s exact mint ramp. Ivory waves are slightly heavier; the lighter palette has less contrast than the earlier dark jade.',
    'collie': 'Sable coat, tipped ears, cream blaze, layered muzzle and eye highlights. Detail is concentrated on expression, as with Prowlarr.',
    'seerr': 'Continuous, restrained lavender pigment bands replace isolated iris scratches; the crescent pupil and matte finish remain.',
    'plex': 'A Hong Kong-centred blue globe with simplified Natural Earth coastlines in Plex yellow. East Asia, Southeast Asia and Australia surround the small ivory play triangle.',
    'tautulli': 'Retained. Its gold and ivory graph is clear at small sizes. The sparse symbol stays lighter than the object illustrations.',
    'grimmory': 'Consistent lavender cover, spine, page edges, metal clasp and ribbon. Details now describe the book’s construction.',
    'audiobookshelf': 'Matching book materials, title rules, page bands and cushioned headphones. The anthropomorphic face is removed for a more mature treatment.',
    'feishin': 'A mint record player replaces the thin isolated glyph. Platter grooves, tonearm and stylus communicate music without relying on a badge.',
    'radarr': 'Radar instrument paired with Sonarr: matching matte bezel and brighter blue screen. Stronger grid markings remain readable at small sizes; mint sweep and warm returns retain priority.',
    'sonarr': 'Sonar instrument paired with Radarr: matching matte bezel and brighter blue screen. Stronger horizon separates the amber submarine from the mint echo arcs.',
    'shelfmark': 'Rose ribbon, stitched margins, eyelet and a real tassel. Shares its fabric and metal colours with the books.',
    'transmission': 'The red handle and ivory housing are retained. The arrow is now centered and uninterrupted, with stripe fragments removed and its stem meeting the shoulders cleanly.',
    'profilarr': 'Five adult figures retain a nearly square lineup, with more natural jaw and face proportions, shaped shoulders, restrained shirt seams and small shared placards.',
    'prowlarr': 'Retained as the mascot reference. Warm fur, cream muzzle, plum facial features and a small number of highlights.',
    'scrutiny': 'Book-family rose frames replace the hotter flamingo pink. Blue lenses and slightly heavier ivory monitoring traces improve small-size coherence.',
    'telegram': 'Retained after the fold review. Matching wing bands and continuous fold faces provide detail with a clear geometric reason.',
}


def main():
    from review_paths import prepare_review
    prepare_review(ROOT)
    catalog = json.loads((ROOT / 'scripts/icons/catalog.json').read_text())
    services = json.loads((ROOT / 'scripts/icons/homepage.json').read_text())
    cards, manifest = [], {}
    for group, names in [('desktop', ['spotify', 'collie']), ('homepage', list(services))]:
        for key in names:
            name = (catalog if group == 'desktop' else services)[key]['name']
            before = ASSETS / 'before' / group / f'{key}.svg'
            after = (THEME if group == 'desktop' else HOMEPAGE) / f'{key}.svg'
            old_url = f'assets/icon-coherence-review/before/{group}/{key}.svg'
            new_url = '../' + str(after.relative_to(ROOT))
            manifest[f'{group}/{key}'] = {
                'before': str(before.relative_to(ROOT)),
                'before_sha256': hashlib.sha256(before.read_bytes()).hexdigest(),
                'after': str(after.relative_to(ROOT)),
                'after_sha256': hashlib.sha256(after.read_bytes()).hexdigest(),
                'critique': NOTES[key],
            }
            cards.append(f'<article><h2>{escape(name)}</h2><div class="pair">'
                         f'<figure><img src="{old_url}" alt="{name} before this pass"><figcaption>Before this pass</figcaption></figure>'
                         f'<figure><img src="{new_url}" alt="Revised {name}"><figcaption>Current</figcaption></figure></div>'
                         f'<p>{escape(NOTES[key])}</p><div class="small">' + ''.join(
                             f'<img src="{new_url}" width="{size}" height="{size}" alt="{name} at {size} px">'
                             for size in (24, 32, 48)) + '</div></article>')
    audit = []
    for key in sorted(catalog, key=lambda k: catalog[k]['name'].casefold()):
        url = f'../home/dot_local/share/icons/rose-punk/scalable/apps/{key}.svg'
        name = escape(catalog[key]['name'])
        audit.append(f'<figure><div><img src="{url}" width="64" height="64" alt="{name} at 64 px">'
                     f'<img src="{url}" width="24" height="24" alt="{name} at 24 px"></div><figcaption>{name}</figcaption></figure>')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rose Punk · Coherence review</title><style>
:root{color-scheme:dark;--size:128px;--surface:#26233a;--ink:#eee9e6;--muted:#bbb3cb}*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--ink);font:15px/1.6 system-ui}header,section{padding:24px 4vw}header{max-width:1050px}h1{font-weight:550;font-size:38px;line-height:1.2}h2{font-size:18px;font-weight:550}p{color:var(--muted)}a{color:#9ccfd8}nav{padding:14px 4vw;position:sticky;top:0;background:var(--surface);border-block:1px solid #77708466;display:flex;gap:20px;align-items:center;flex-wrap:wrap;z-index:1}select{padding:7px;background:var(--surface);color:var(--ink);border:1px solid #777084;border-radius:6px;font:inherit}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:24px}.cards article{padding:20px;background:#201c2d;border-radius:12px}.pair{display:flex;justify-content:space-evenly;gap:12px}figure{margin:0;text-align:center}.pair img{width:var(--size);height:var(--size);max-width:100%}figcaption{color:var(--muted);font-size:12px}.small{display:flex;gap:24px;justify-content:center;align-items:center}.critique{max-width:1050px}.critique li{margin:12px 0}.audit{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:28px 14px}.audit figure div{display:flex;justify-content:center;gap:12px;align-items:center;height:80px}.reference{display:flex;gap:25px;align-items:center;flex-wrap:wrap}.reference img{width:80px;height:80px}@media(max-width:500px){h1{font-size:30px}.cards{grid-template-columns:1fr}}
</style><body><header><h1>One material language, different identities.</h1>
<p>Review of all COUNT primary frameless icons and 14 Homepage icons. The common rules are filled silhouettes, clean internal features, restrained material shading, warm ivory highlights and useful detail. Material gradients describe a surface; they should not turn every mark into a glossy button.</p>
<div class="reference"><figure><img src="../home/dot_local/share/icons/rose-punk/scalable/apps/camera.svg" alt="Camera reference"><figcaption>Material reference</figcaption></figure><figure><img src="../home/dot_local/share/icons/rose-punk/scalable/apps/prowlarr.svg" alt="Prowlarr reference"><figcaption>Mascot reference</figcaption></figure><figure><img src="../home/dot_local/share/icons/rose-punk/scalable/apps/audio-player.svg" alt="Audio Player reference"><figcaption>Mint reference</figcaption></figure></div></header>
<nav><label>Compare size <select id="size"><option>48</option><option>64</option><option>96</option><option selected>128</option></select> px</label><a href="#changes">Changes</a><a href="#critique">Critical findings</a><a href="#audit">Whole desktop set</a><a href="rose-punk-icons-frameless.html">Primary study</a><a href="rose-punk-homepage-review.html">Homepage originals</a></nav>
<section id="critique" class="critique"><h2>Critical findings</h2><ul>
<li><strong>Colour:</strong> Spotify now matches Audio Player exactly. The server artwork repeats mint, rose, amber, lavender and blue glass instead of introducing a separate palette per service. Electric blue remains a deliberate Zed Preview accent.</li>
<li><strong>Detail:</strong> Collie now matches Prowlarr’s facial construction. Server details describe pages, fabric, glass, instrument readings and music hardware. Seerr uses a cropped anime iris rather than an unrelated eye silhouette.</li>
<li><strong>Weight:</strong> Radarr and Sonarr now make a coherent pair. Feishin has enough mass beside them. Profilarr now has a nearly square footprint through taller torsos, without stretching the faces. Scrutiny remains intentionally wide and lighter than the square instruments.</li>
<li><strong>Remaining material outliers:</strong> Problem Reporting’s broad glow, Flatseal’s shaded seal, Volume Control’s knob bevel and Tour’s glossy balloon remain more polished than the Camera-led objects. The next targeted pass should simplify those highlights while retaining the objects.</li>
<li><strong>Identity exceptions:</strong> Tautulli, Steam, Zed, Tailscale and the Tjik marks are intentionally simpler than object illustrations. Keep their characteristic geometry; do not add decorative grain just to equalise detail. Their stroke weight and optical size matter more.</li>
<li><strong>Background limits:</strong> The set is tuned for plum surfaces. Tautulli’s ivory branches and other pale unbacked marks lose definition on off-white; a light-theme export would need deliberate darker accents, not a universal outline.</li>
<li><strong>Small-size limit:</strong> At 24 px, Profilarr communicates a group rather than five readable expressions, and thin monitoring traces become secondary. Spotify’s requested pale mint has lower white-mark contrast than dark jade. The silhouettes and large features must carry recognition.</li>
</ul><p>These are source-artwork changes and review artifacts. This pass does not deploy Homepage or regenerate the future secondary framed theme. The historical framed comparison is not an approval preview for that future set.</p></section>
<section id="changes"><h2>Before this pass → current</h2><p><a href="assets/icon-coherence-review/size-check.png">Rendered size and background checks</a> · <a href="assets/icon-homepage-review/icons.png">Server set overview</a></p><div class="cards">CARDS</div></section>
<section id="audit"><h2>All COUNT desktop identities · 64 and 24 px</h2><div class="audit">AUDIT</div></section>
<script>document.querySelector('#size').addEventListener('change',e=>document.documentElement.style.setProperty('--size',e.target.value+'px'));</script></body></html>'''
    (ROOT / '.local/icon-reviews/docs/rose-punk-coherence-review.html').write_text(
        html.replace('COUNT', str(len(catalog))).replace('CARDS', ''.join(cards)).replace('AUDIT', ''.join(audit)))
    (ASSETS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Wrote coherence review: {len(catalog)} desktop identities, {len(manifest)} comparisons')


if __name__ == '__main__':
    main()
