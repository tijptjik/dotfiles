#!/usr/bin/env python3
"""Rebuild the final consistency review from committed selections and generated SVGs.

Run after release.py build/check. All preview artifacts remain ignored.
"""
from pathlib import Path
import sys,json,hashlib,math,base64
from html import escape
from collections import Counter

from frameless import render
from PIL import Image,ImageDraw,ImageFont
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / '.local/icon-reviews/docs/rose-punk-consistency-review'
OUT.mkdir(parents=True, exist_ok=True)
selection = json.loads((HERE / 'review-selections.json').read_text())
SIZES=[24,32,48,64,96];SURFACES={'dark':'#191724','plum':'#34304f','ivory':'#fffaf2','white':'#ffffff'}
font=ImageFont.truetype('DejaVuSans.ttf',13);small=ImageFont.truetype('DejaVuSans.ttf',11);head=ImageFont.truetype('DejaVuSans.ttf',22)
items=[];cache={}
for selected in selection['icons']:
 i = dict(selected)
 i['path'] = str(ROOT / i['output'])
 t = Path(i['path']).read_text()
 assert hashlib.sha256(t.encode()).hexdigest() == i['suggested_sha256'], i['id']
 items.append(i)
 for size in SIZES:
  cache[i['id'], size] = render(t, size)
assert len(items)==len({i['id'] for i in items})==167
byid={i['id']:i for i in items}
def paste(im,k,size,x,y):
 r=cache[k,size];im.paste(r,(int(x),int(y)),r)
def lum(rgb):
 c=[v/255 for v in rgb];c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c];return sum(v*w for v,w in zip(c,[.2126,.7152,.0722]))
def contrast(a,b):
 a,b=sorted([lum(a),lum(b)]);return (b+.05)/(a+.05)
metrics=[]
for i in items:
 im=cache[i['id'],64];pix=list(im.getdata());area=sum(p[3]/255 for p in pix);cx=sum((j%64+.5)*p[3]/255 for j,p in enumerate(pix))/area;cy=sum((j//64+.5)*p[3]/255 for j,p in enumerate(pix))/area
 a=im.getchannel('A');box=a.point(lambda x:255 if x>=8 else 0).getbbox();colors=Counter(p[:3] for p in pix if p[3]>245)
 low={}
 for name,bg in SURFACES.items():
  rgb=tuple(int(bg[j:j+2],16) for j in (1,3,5));low[name]=round(sum(n for col,n in colors.items() if contrast(col,rgb)<3)/sum(colors.values()),3)
 metrics.append({'id':i['id'],'number':i['priority'],'name':i['name'],'bounds_64':box,'alpha_area_64':round(area,1),'centroid_64':[round(cx,2),round(cy,2)],'low_contrast_opaque_fraction_against_canvas':low,'note':'Canvas contrast is a triage metric only; internal marks may be protected by their own backing.'})
# Complete catalog at actual 64 and 24 pixels, equal cells and no per-icon resizing.
for surface,bg in SURFACES.items():
 ink='#34304f' if surface in ['ivory','white'] else '#fff0da'
 for page in range(4):
  part=items[page*42:(page+1)*42];im=Image.new('RGB',(1200,1150),bg);d=ImageDraw.Draw(im)
  d.text((20,16),f'Rose Punk / selected set / {surface} / {page+1} of 4',font=head,fill=ink)
  d.text((20,48),'Actual 64 px and 24 px · material redesigns, terminal identities and overlapping categories',font=font,fill=ink)
  for j,i in enumerate(part):
   x=j%6*200;y=80+j//6*150;paste(im,i['id'],64,x+35,y+15);paste(im,i['id'],24,x+130,y+36)
   d.text((x+10,y+93),f"{i['priority']}. {i['name']}"[:29],font=font,fill=ink)
  im.save(OUT/f'catalog-{surface}-{page+1}.png')
GROUPS = selection['groups']
LABELS = selection.get('group_labels', {})
for stale in OUT.glob('family-*.png'):
 if not any(stale.name == f'family-{group}-{surface}.png' for group in GROUPS for surface in SURFACES):
  stale.unlink()
for name,keys in GROUPS.items():
 for surface,bg in SURFACES.items():
  ink='#34304f' if surface in ['ivory','white'] else '#fff0da';im=Image.new('RGB',(930,90+110*len(keys)),bg);d=ImageDraw.Draw(im)
  d.text((18,16),f'{LABELS.get(name, name)} / {surface}',font=head,fill=ink)
  for size,x in zip(SIZES,[310,390,480,590,740]):d.text((x,54),f'{size} px',font=font,fill=ink)
  for j,k in enumerate(keys):
   y=85+j*110;i=byid[k];d.text((18,y+35),f"{i['priority']}. {i['name']}",font=font,fill=ink)
   for size,x in zip(SIZES,[310,390,480,590,740]):paste(im,k,size,x,y+(96-size)//2)
  im.save(OUT/f'family-{name}-{surface}.png')
(OUT/'metrics.json').write_text(json.dumps({'caution':'Contrast/area/centroid are screening measures, not an automatic design score. Visual review determines whether a weak pixel belongs to an essential mark.','icons':metrics},indent=2)+'\n')
(OUT/'manifest.json').write_text(json.dumps({'scope':'Integrated authoritative artwork; release and deployment remain separate.','sizes':SIZES,'surfaces':SURFACES,'icons':items},indent=2)+'\n')
cards=[]
for i in items:
 data=base64.b64encode(Path(i['path']).read_bytes()).decode();cards.append(f'<article data-id="{i["id"]}" data-name="{escape(i["name"].lower())}"><img src="data:image/svg+xml;base64,{data}" alt="{escape(i["name"])}"><span>{i["priority"]}. {escape(i["name"])}</span><small>{escape(i["decision"])}</small></article>')
html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Rose Punk — final consistency review</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{box-sizing:border-box}body{margin:0;background:#191724;color:#fff0da;font:15px/1.5 system-ui}header{padding:20px 28px}h1{margin:0;font-size:28px}nav{padding:14px 28px;position:sticky;top:0;background:inherit;display:flex;gap:18px;flex-wrap:wrap;border-block:1px solid #8886}select,input{font:inherit;background:inherit;color:inherit;border:1px solid #888;padding:4px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:16px;padding:24px}article{min-height:170px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;text-align:center}article img{width:var(--sz,64px);height:var(--sz,64px)}small{font-size:10px;opacity:.7}a{color:inherit}article[hidden]{display:none}</style><header><h1>Rose Punk: final consistency review</h1><p>All 167 selected icons, ordered by family and purpose. TjikOS comes first: Greetjik opens the group, Gmailtjik and Mailtjik close it. Terminal Apps, Brand Marks - Solid and Brand Marks - Open follow, then Starfix, Craft, Everyday desktop, System and hardware, Media and graphics, and Developer tools. Each icon appears once in the full review. The seven accepted studies are integrated into the build. The newer gold and jade keys are retained, with the ring threaded through both holes. Fish now pairs with Kitty as a flat jade silhouette with a single chevron fin. The latest pass also simplifies mechanical detail and small marks, and retains the matching Calendar pair. Categories overlap: an icon may appear in several groups. Chezmoi and Chezetc appear in System and hardware. 24 retained originals remain unchanged. Craft whites are brighter, with filled edges replacing enclosing outlines.</p><p><a href="report.html">Read the findings and close-up evidence</a></p></header><nav><label>Size <select id="size"><option>24</option><option>32</option><option>48</option><option selected>64</option><option>96</option></select></label><label>Surface <select id="surface"><option>dark</option><option>plum</option><option>ivory</option><option>white</option></select></label><label>Category <select id="family"><option value="all">All 167</option>'''+''.join(f'<option value="{k}">{escape(LABELS.get(k, k))}</option>' for k in GROUPS)+'''</select></label><input id="search" type="search" placeholder="Find an icon" aria-label="Find an icon"></nav><main>'''+''.join(cards)+'''</main><script>const groups='''+json.dumps(GROUPS)+''';const surfaces={dark:['#191724','#fff0da'],plum:['#34304f','#fff0da'],ivory:['#fffaf2','#34304f'],white:['#ffffff','#34304f']};document.querySelector('#size').onchange=e=>document.documentElement.style.setProperty('--sz',e.target.value+'px');document.querySelector('#surface').onchange=e=>{let [bg,fg]=surfaces[e.target.value];document.body.style.background=bg;document.body.style.color=fg};function filter(){let g=document.querySelector('#family').value,q=document.querySelector('#search').value.toLowerCase();document.querySelectorAll('article').forEach(n=>n.hidden=(g!=='all'&&!groups[g].includes(n.dataset.id))||!n.dataset.name.includes(q))}document.querySelector('#family').onchange=filter;document.querySelector('#search').oninput=filter;</script></html>'''
(OUT/'index.html').write_text(html)
print(f'Rendered 167 icons at five sizes; 16 catalog sheets, {len(GROUPS) * 4} category sheets, metrics and interactive review.')
print('Highest light-surface low-contrast fractions (triage, not failures):')
for i in sorted(metrics,key=lambda x:x['low_contrast_opaque_fraction_against_canvas']['white'],reverse=True)[:18]:print(i['id'],i['low_contrast_opaque_fraction_against_canvas']['white'])

from consistency_report import write_report
write_report(OUT, selection, metrics)
