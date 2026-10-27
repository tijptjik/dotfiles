#!/usr/bin/env python3
"""Render the primary frameless catalog offline from validated, vendored sources."""
import colorsys
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from build import ART, ROOT
from extra_art import ART as EXTRA
from illustrated import icon as original_icon, DEST
from palette import apply_paint_overrides, load_palette
from materials import finish, source_pigment
from frameless import normalize
from material_art import artwork as material_artwork, details
from icon_data import HERE, aliases_for, load_catalog, write_file, write_tree
from command_icons import render as render_command_icons

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
    # A few upstream clip shapes refer to deleted editor paint servers.
    # Clipping uses geometry, so normalize only unresolved clip paint, retaining
    # the vendored source and all rendered shapes unchanged.
    if key != 'camera':
        known_ids = {node.get('id') for node in root.iter()}
        for clip in root.iter(f'{{{SVG}}}clipPath'):
            for node in clip.iter():
                for attr in ('fill', 'stroke', 'style'):
                    if node.get(attr):
                        node.set(attr, re.sub(r'url\(#([^)]*)\)',
                            lambda m: m.group() if m[1] in known_ids else '#ffffff', node.get(attr)))
    if entry['mode'] == 'brand':
        for node in root.iter():
            if node.tag.split('}')[-1] in ('path','circle','ellipse','polygon','rect'):
                node.set('fill','url(#enamel)')
        root.set('fill','url(#enamel)')
        content = ET.tostring(root,encoding='unicode')
    else:
        content = ET.tostring(root,encoding='unicode')
        def rgb_to_hex(match):
            vals=[v.strip() for v in match.group(1).split(',')]
            return '#'+''.join(f"{max(0,min(255,round(float(v.rstrip('%'))*(2.55 if '%' in v else 1)))):02x}" for v in vals)
        content = re.sub(r'rgb\(([^)]+)\)', rgb_to_hex, content)
        content = re.sub(r'#[0-9a-fA-F]{6}(?![\w-])|#[0-9a-fA-F]{3}(?![\w-])', tint if key == 'camera' else source_pigment, content)
        content = content.replace('currentColor','#d1c0ee')
    # Prevent upstream gradient IDs from colliding with the tile gradients.
    if entry['mode'] != 'brand':
        ids = re.findall(r'\bid="([^"]+)"', content)
        for ident in sorted(ids,key=len,reverse=True):
            content=content.replace(f'id="{ident}"',f'id="src-{ident}"').replace(f'#{ident}"',f'#src-{ident}"').replace(f'#{ident})',f'#src-{ident})')
    return original_icon(key,'').replace('</svg>',content+'</svg>')


def render():
    catalog = load_catalog()
    aliases = aliases_for(catalog)
    outputs = {}
    original={**ART,**EXTRA}
    config, _, _, _, family, recolor, adapted = load_palette()
    for key,entry in catalog.items():
        authored = material_artwork(key)
        if authored is not None:
            output = original_icon(key, '').replace('</svg>', authored + '</svg>')
        elif entry['mode']=='reference':
            output=adapted(entry['reference'], family(key))
        elif entry['mode']=='outline':
            root=ET.fromstring((HERE/entry['geometry']).read_text())
            root.set('x','8');root.set('y','8');root.set('width','48');root.set('height','48')
            root.set('preserveAspectRatio','xMidYMid meet')
            root.set('stroke','#b39bd9')
            root.set('stroke-width','2')
            output=original_icon(key,'').replace('</svg>',ET.tostring(root,encoding='unicode')+'</svg>')
        elif entry['mode']=='illustrated-local':
            root=ET.fromstring((HERE/entry['geometry']).read_text())
            artwork=''.join(ET.tostring(n,encoding='unicode') for n in root)
            output=original_icon(key,'').replace('</svg>',artwork+'</svg>')
        elif entry['mode']=='identity':
            output=recolor((HERE/entry['geometry']).read_text(),family(key))
        elif entry['mode']=='original':
            output=recolor(original_icon(key,original[key][1]),family(key))
        else:
            imported = imported_icon(key, entry)
            output = recolor(imported, family(key)) if key == 'camera' or entry['mode'] == 'brand' else imported
        output = apply_paint_overrides(output, config.get('paint_overrides', {}))
        output = finish(output, key)
        if details(key):
            output = output.rsplit('</svg>', 1)[0] + details(key) + '</svg>\n'
        output, _ = normalize(output)
        ET.fromstring(output)
        outputs[f'{key}.svg'] = output.encode()
        outputs[f'symlink_rose-punk-{key}.svg'] = (key + '.svg\n').encode()
    for alias, key in aliases.items():
        if alias != key and alias not in catalog:
            outputs[f'symlink_{alias}.svg'] = (key + '.svg\n').encode()
    command_outputs, _ = render_command_icons()
    outputs.update(command_outputs)
    return outputs, aliases


def main():
    outputs, aliases = render()
    write_tree(DEST, outputs)
    write_file(HERE / 'theme-aliases.json', (json.dumps(aliases, indent=2, sort_keys=True) + '\n').encode())
    catalog = load_catalog()
    print(f'Built {len(catalog)} primary frameless icons and {len(aliases)} app-name aliases')


if __name__=='__main__':main()
