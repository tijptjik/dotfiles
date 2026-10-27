#!/usr/bin/env python3
"""Generate the searchable illustrated icon catalog and paged SVG contact sheets."""
import json,re
from html import escape
from pathlib import Path
from build import ROOT
from illustrated import DEST


def sheet(keys,catalog,title):
    items=[]
    for i,key in enumerate(keys):
        x=24+(i%6)*172;y=106+(i//6)*142
        svg=(DEST/f'{key}.svg').read_text().split('>',1)[1].rsplit('</svg>',1)[0]
        ids=re.findall(r'\bid="([^"]+)"',svg)
        for ident in sorted(set(ids),key=len,reverse=True):
            svg=svg.replace(f'id="{ident}"',f'id="{key}-{ident}"').replace(f'#{ident}"',f'#{key}-{ident}"').replace(f'#{ident})',f'#{key}-{ident})')
        items.append(f'<g transform="translate({x+38} {y}) scale(1.4)">{svg}</g>')
        name=catalog[key]['name']
        if len(name)>23:name=name[:21]+'…'
        items.append(f'<text x="{x+82}" y="{y+114}" text-anchor="middle" fill="#e5e5e5" font-size="13">{escape(name)}</text>')
    height=120+((len(keys)+5)//6)*142
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{height}" viewBox="0 0 1080 {height}"><rect width="1080" height="{height}" fill="#191724"/><g font-family="sans-serif"><text x="32" y="50" fill="#e56ea1" font-size="28">{escape(title)}</text><text x="32" y="78" fill="#c4b5db" font-size="14">Rose Punk Illustrated · Authentic silhouettes · Local review</text>'+''.join(items)+'</g></svg>'


def main():
    from review_paths import prepare_review
    prepare_review(ROOT)
    catalog=json.loads((ROOT/'scripts/icons/catalog.json').read_text())
    keys=sorted(catalog,key=lambda k:(not catalog[k]['installed'],catalog[k]['name'].lower()))
    cards=[]
    for key in keys:
        c=catalog[key];name=escape(c['name']);kind='Installed' if c['installed'] else 'Extra coverage'
        cards.append(f'<article data-name="{name.lower()}" data-kind="{kind}"><img src="../home/dot_local/share/icons/rose-punk-illustrated/scalable/apps/{key}.svg" alt="{name}"><h2>{name}</h2><small>{kind}</small></article>')
    (ROOT / '.local/icon-reviews/docs/rose-punk-icons-gallery.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rose Punk Illustrated · Full catalog</title><style>
:root{color-scheme:dark;--size:80px}body{margin:0;background:#191724;color:#e5e5e5;font:16px system-ui}header{position:sticky;top:0;background:#191724f5;padding:24px 32px;border-bottom:1px solid #393047}h1{color:#e56ea1;margin:0 0 8px;font-size:26px}p,small{color:#c4b5db}input,select,button{background:#232032;color:#e5e5e5;border:1px solid #68516c;border-radius:8px;padding:10px;margin-right:8px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:12px;padding:24px 32px}article{text-align:center;padding:20px 8px;background:#211b2e;border:1px solid #393047;border-radius:16px}article[hidden]{display:none}img{width:var(--size);height:var(--size)}h2{font-size:14px;font-weight:500;margin:12px 0 4px}small{font-size:11px}label{white-space:nowrap}footer{padding:24px 32px;color:#c4b5db}a{color:#e56ea1}
</style><header><h1>Rose Punk / Illustrated</h1><p>102 installed app families · 127 desktop entries · 10 extra apps</p><input id="search" type="search" placeholder="Find an application" aria-label="Find an application"><select id="kind" aria-label="Coverage"><option value="">All apps</option><option>Installed</option><option>Extra coverage</option></select><label>Size <select id="size"><option>24</option><option>32</option><option>48</option><option>64</option><option selected>80</option><option>96</option></select> px</label></header><main>'''+''.join(cards)+'''</main><footer><a href="rose-punk-icon-style-prompt.md">Reusable style prompt</a> · Original brand geometry and source attribution are recorded in the repository.</footer><script>
const filter=()=>{let q=document.querySelector('#search').value.toLowerCase(),k=document.querySelector('#kind').value;for(const a of document.querySelectorAll('article'))a.hidden=!a.dataset.name.includes(q)||(k&&a.dataset.kind!==k);};document.querySelector('#search').addEventListener('input',filter);document.querySelector('#kind').addEventListener('change',filter);document.querySelector('#size').addEventListener('change',e=>document.documentElement.style.setProperty('--size',e.target.value+'px'));
</script></html>''')
    for i in range(0,len(keys),30):
        (ROOT/f'.local/icon-reviews/docs/rose-punk-icons-catalog-{i//30+1}.svg').write_text(sheet(keys[i:i+30],catalog,f'Rose Punk / Illustrated / {i//30+1}'))
    (ROOT / '.local/icon-reviews/docs/rose-punk-icons-redrawn.svg').write_text(sheet(['firefox','mullvad','thunderbird','gimp','transmission'],catalog,'Five redrawn identities'))


if __name__=='__main__':main()
