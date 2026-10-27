#!/usr/bin/env python3
"""Generate a local A/B review at actual launcher sizes and a static contact sheet."""
from pathlib import Path
from html import escape
from build import ART, ROOT, icon
from illustrated import DEST


def main():
    from review_paths import prepare_review
    prepare_review(ROOT)
    cards=[]
    svg=[]
    for i,(key,(name,mark)) in enumerate(ART.items()):
        a='../home/dot_local/share/icons/rose-punk/scalable/apps/'+key+'.svg'
        b='../home/dot_local/share/icons/rose-punk-illustrated/scalable/apps/'+key+'.svg'
        cards.append(f'<article><h2>{escape(name)}</h2><div class="pair"><figure><img src="{a}" alt="{escape(name)} outline"><figcaption>A · Outline</figcaption></figure><figure><img src="{b}" alt="{escape(name)} illustrated"><figcaption>B · Illustrated</figcaption></figure></div></article>')
        x=24+i%5*240;y=120+i//5*160
        for column,content in enumerate((icon(mark),(DEST / f'{key}.svg').read_text())):
            inner=content.split('>',1)[1].rsplit('</svg>',1)[0]
            # Namespace gradients per embedded icon in the combined document.
            for ident in ('tile','enamel','ink','gem'):
                inner=inner.replace('id="'+ident+'"',f'id="{key}-{ident}"').replace('url(#'+ident+')',f'url(#{key}-{ident})')
            svg.append(f'<g transform="translate({x+18+column*106} {y}) scale(1.3)">{inner}</g>')
        svg.append(f'<text x="{x+112}" y="{y+112}" text-anchor="middle" fill="#e5e5e5" font-size="15">{escape(name)}</text>')
    (ROOT / '.local/icon-reviews/docs/rose-punk-icons-compare.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Rose Punk · A / B</title>
<style>
:root{color-scheme:dark;--size:64px}*{box-sizing:border-box}body{margin:0;background:#191724;color:#e5e5e5;font:16px system-ui,sans-serif}header{position:sticky;top:0;background:#191724f5;border-bottom:1px solid #393047;padding:24px 32px;z-index:2}h1{font-size:26px;color:#e56ea1;margin:0 0 8px}p{color:#c4b5db;margin:8px 0}nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}button{border:1px solid #64516e;background:#232032;color:#e5e5e5;border-radius:8px;padding:8px 14px;cursor:pointer}button[aria-pressed=true]{background:#e56ea1;color:#191724;border-color:#e56ea1}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;padding:24px 32px}article{border:1px solid #393047;border-radius:16px;padding:16px;background:#1f1b2b}h2{font-size:16px;text-align:center;font-weight:500;margin:0 0 18px}.pair{display:flex;justify-content:space-evenly;align-items:center;min-height:142px;gap:8px}figure{margin:0;text-align:center}img{width:var(--size);height:var(--size);max-width:100%;transition:width .15s,height .15s}figcaption{font-size:12px;color:#b7a6c6;margin-top:12px}footer{padding:8px 32px 32px;color:#b7a6c6}code{color:#f4b7c9}body.light{background:#e5e5e5}body.light article{background:#d6cfe1}body.light h2{color:#232032}body.light figcaption{color:#51405c}
</style><header><h1>Rose Punk / Two directions</h1><p>A — crisp outlines. B — filled enamel, layered color and soft highlights.</p><p>Same 25 apps and silhouettes. Compare the small sizes before choosing.</p><nav aria-label="Preview size">'''+''.join(f'<button aria-pressed="{str(n==64).lower()}" data-size="{n}">{n}px</button>' for n in (24,32,48,64,96))+'''<button id="background" aria-pressed="false">Light background</button></nav></header><main>'''+''.join(cards)+'''</main><footer>Local review · Both directions are editable SVGs.<br>To review the application icons: <code>python3 scripts/icons/choose.py a</code> or <code>python3 scripts/icons/choose.py b</code></footer><script>
for(const button of document.querySelectorAll('[data-size]'))button.addEventListener('click',()=>{document.documentElement.style.setProperty('--size',button.dataset.size+'px');for(const b of document.querySelectorAll('[data-size]'))b.setAttribute('aria-pressed',String(b===button));});document.querySelector('#background').addEventListener('click',e=>{const on=document.body.classList.toggle('light');e.target.setAttribute('aria-pressed',String(on));});
</script></html>''')
    (ROOT / '.local/icon-reviews/docs/rose-punk-icons-compare.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1248" height="960" viewBox="0 0 1248 960"><rect width="1248" height="960" fill="#191724"/><g font-family="sans-serif"><text x="32" y="52" fill="#e56ea1" font-size="28">ROSE PUNK / A · OUTLINE / B · ILLUSTRATED</text><text x="32" y="84" fill="#c4b5db" font-size="16">Every pair: A on the left · B on the right</text>'+''.join(svg)+'</g></svg>')


if __name__=='__main__':main()
