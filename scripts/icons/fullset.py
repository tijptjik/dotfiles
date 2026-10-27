#!/usr/bin/env python3
"""Build the illustrated catalog from vendored SVG geometry and original artwork."""
import colorsys
import copy
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from build import ART, ROOT
from extra_art import ART as EXTRA
from illustrated import icon as original_icon, DEST

HERE = Path(__file__).resolve().parent
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)


def tint(match):
    raw = match.group(0)[1:]
    if len(raw) == 3:
        raw = ''.join(c * 2 for c in raw)
    rgb = tuple(int(raw[i:i+2],16)/255 for i in (0,2,4))
    hue,saturation,value = colorsys.rgb_to_hsv(*rgb)
    if value < .18:
        return '#35213f'
    if value > .9 and saturation < .18:
        return '#f4dce9'
    # Preserve the original highlights and shading while narrowing the palette.
    cool = .35 < hue < .8
    low = (76,51,103) if cool else (117,39,81)
    high = (217,195,242) if cool else (244,183,201)
    amount = max(0,min(1,(value-.15)/.85))
    return '#' + ''.join(f'{round(a+(b-a)*amount):02x}' for a,b in zip(low,high))


def imported_icon(key, entry):
    source = HERE / entry['geometry']
    text = source.read_text()
    root = ET.fromstring(text)
    # Keep vector shapes and gradients, omit editor-only metadata.
    for child in list(root):
        if child.tag.split('}')[-1] in ('metadata','namedview','title','desc'):
            root.remove(child)
    if 'viewBox' not in root.attrib:
        def size(name):
            return re.match(r'[\d.]+',root.get(name,'128')).group(0)
        root.set('viewBox',f'0 0 {size("width")} {size("height")}')
    root.set('width','46');root.set('height','46');root.set('x','9');root.set('y','8')
    root.set('preserveAspectRatio','xMidYMid meet')
    for name in list(root.attrib):
        if name.startswith('{') or name in ('id','version'):
            del root.attrib[name]
    # Inline upstream CSS before embedding: classes must not leak across a contact sheet.
    rules = {}
    for node in root.iter():
        if node.tag.split('}')[-1] == 'style' and node.text:
            for names, body in re.findall(r'([^{}]+)\{([^{}]+)\}', node.text):
                for name in names.split(','):
                    if name.strip().startswith('.'):
                        rules[name.strip()[1:]] = body.strip()
    for node in root.iter():
        declarations = [rules[c] for c in node.get('class','').split() if c in rules]
        if declarations:
            node.set('style',';'.join(declarations+[node.get('style','')]))
        node.attrib.pop('class',None)
        for child in list(node):
            if child.tag.split('}')[-1] == 'style':node.remove(child)
    if entry['mode'] == 'brand':
        for node in root.iter():
            if node.tag.split('}')[-1] in ('path','circle','ellipse','polygon','rect'):
                node.set('fill','url(#enamel)')
        root.set('fill','url(#enamel)')
        # A small shadow gives the logo the same raised finish as the original B set.
        shadow = copy.deepcopy(root)
        shadow.set('y','10')
        for node in shadow.iter():
            if 'fill' in node.attrib:node.set('fill','#100d1c')
        content = ET.tostring(shadow,encoding='unicode') + ET.tostring(root,encoding='unicode')
    else:
        content = ET.tostring(root,encoding='unicode')
        def rgb_to_hex(match):
            vals=[v.strip() for v in match.group(1).split(',')]
            return '#'+''.join(f"{max(0,min(255,round(float(v.rstrip('%'))*(2.55 if '%' in v else 1)))):02x}" for v in vals)
        content = re.sub(r'rgb\(([^)]+)\)', rgb_to_hex, content)
        content = re.sub(r'#[0-9a-fA-F]{6}(?![\w-])|#[0-9a-fA-F]{3}(?![\w-])', tint, content)
        content = content.replace('currentColor','#d1c0ee')
    # Prevent upstream gradient IDs from colliding with the tile gradients.
    if entry['mode'] != 'brand':
        ids = re.findall(r'\bid="([^"]+)"', content)
        for ident in sorted(ids,key=len,reverse=True):
            content=content.replace(f'id="{ident}"',f'id="src-{ident}"').replace(f'#{ident}"',f'#src-{ident}"').replace(f'#{ident})',f'#src-{ident})')
    return original_icon(key,'').replace('</svg>',content+'</svg>')


def main():
    catalog=json.loads((HERE/'catalog.json').read_text())
    aliases={name:key for name,key in json.loads((HERE/'theme-aliases.json').read_text()).items() if not any(c.isspace() for c in name)}
    original={**ART,**EXTRA}
    for key,entry in catalog.items():
        if entry['mode']=='original':
            output=original_icon(key,original[key][1])
        else:
            output=imported_icon(key,entry)
        ET.fromstring(output)
        (DEST/f'{key}.svg').write_text(output)
        (DEST/f'symlink_rose-punk-{key}.svg').write_text(key+'.svg\n')
        for name in entry['icon_names']:
            name=name.removesuffix('.svg').removesuffix('.png')
            if '/' not in name and name and not any(c.isspace() for c in name) and not name.startswith('rose-punk-'):
                aliases[name]=key
        for desktop in entry['desktop_ids']:
            name=desktop.removesuffix('.desktop')
            if not any(c.isspace() for c in name):
                aliases[name]=key
    for alias,key in aliases.items():
        if alias != key and alias not in catalog:
            (DEST/f'symlink_{alias}.svg').write_text(key+'.svg\n')
    (HERE/'theme-aliases.json').write_text(json.dumps(aliases,indent=2,sort_keys=True)+'\n')
    print(f'Built {len(catalog)} illustrated icons and {len(aliases)} app-name aliases')


if __name__=='__main__':main()
