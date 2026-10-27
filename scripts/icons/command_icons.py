#!/usr/bin/env python3
"""Build original, frameless launcher-command companions to Rose Punk."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from frameless import normalize, render as rasterize
from material_art import command_artwork
from icon_data import HERE, ROOT, PRIMARY, REVIEWS, write_file

DEST = PRIMARY / 'scalable/apps'
SVG = 'http://www.w3.org/2000/svg'
COMMANDS = {
    'refresh': ('Refresh index', ['/refresh'], 'Jade and copper return arrows around ivory index cards'),
    'pin': ('Pin launcher', ['/pin'], 'Copper and rose thumbtack with a cool steel point'),
    'grid': ('Grid view', ['/grid'], 'Four pigment-coloured application cards'),
    'list': ('List view', ['/list'], 'Ivory list slips with coordinated colour tabs'),
    'stats': ('Usage statistics', ['/stats'], 'Folded chart paper with jade, violet and copper bars'),
    'config': ('Configuration', ['/config'], 'Three steel slider rails with pigment-coloured controls'),
    'shortcuts': ('Keyboard shortcuts', ['/shortcuts', '/bindings'], 'Ivory and violet arrow-key caps'),
}


def render():
    outputs, manifest = {}, {}
    for key, (name, commands, description) in COMMANDS.items():
        source = ('<svg xmlns="' + SVG + '" width="64" height="64" viewBox="0 0 64 64">'
                  + '<title>' + name + '</title><desc>Original Rose Punk artwork. ' + description + '.</desc>'
                  + '<rect id="tile" x="3" y="2" width="58" height="58"/>'
                  + command_artwork(key) + '</svg>')
        output, sizing = normalize(source)
        icon = 'runtjik-' + key
        outputs[icon + '.svg'] = output.encode()
        outputs['symlink_rose-punk-' + icon + '.svg'] = (icon + '.svg\n').encode()
        manifest[icon] = {
            'name': name, 'commands': commands, 'description': description,
            'source': 'scripts/icons/local/' + icon + '.svg',
            'authored_in': 'scripts/icons/material_art.py:COMMAND_ART',
            'license': 'Original artwork',
            'sha256': hashlib.sha256(output.encode()).hexdigest(), 'sizing': sizing,
        }
    return outputs, manifest


def build():
    outputs, manifest = render()
    # This companion build owns only these files, never the application folder.
    for name, data in outputs.items():
        write_file(DEST / name, data)
        if not name.startswith('symlink_'):
            write_file(HERE / 'local' / name, data)
    write_file(HERE / 'command-icons.json', (json.dumps(manifest, indent=2) + '\n').encode())
    return manifest


def preview(manifest):
    REVIEWS.mkdir(parents=True, exist_ok=True)
    camera = REVIEWS / 'assets/icon-material-review/before/camera.svg'
    camera_hash = hashlib.sha256(camera.read_bytes()).hexdigest()
    sheet = ET.Element(f'{{{SVG}}}svg', {'width': '1100', 'height': '1080', 'viewBox': '0 0 1100 1080'})
    ET.SubElement(sheet, f'{{{SVG}}}rect', {'width': '1100', 'height': '1080', 'fill': '#191724'})

    def label(value, x, y, size=14, fill='#e0def4'):
        text = ET.SubElement(sheet, f'{{{SVG}}}text', {'x': str(x), 'y': str(y), 'font-family': 'sans-serif',
                                           'font-size': str(size), 'fill': fill})
        text.text = value

    label('Rose Punk · launcher commands', 24, 37, 24)
    label('Original editable objects · transparent 64 × 64 · unchanged camera reference', 24, 62, 13, '#908caa')
    sizes = [(24, 280), (32, 410), (48, 540), (64, 680), (96, 850)]
    for size, x in sizes:
        label(str(size) + ' px', x, 94, 13, '#908caa')
    rows = [('Camera reference', 'unchanged frozen reference', camera)]
    rows += [(entry['commands'][0], entry['name'], ROOT / entry['source']) for entry in manifest.values()]
    for index, (name, description, path) in enumerate(rows):
        y = 106 + index * 118
        label(name, 24, y + 41, 16)
        label(description, 24, y + 62, 12, '#908caa')
        for size, x in sizes:
            node = ET.fromstring(path.read_text())
            prefix = f'row{index}-size{size}-'
            ids = {n.get('id'): prefix + n.get('id') for n in node.iter() if n.get('id')}
            for n in node.iter():
                for attr, value in list(n.attrib.items()):
                    if attr == 'id':
                        value = ids[value]
                    elif value.startswith('#') and value[1:] in ids:
                        value = '#' + ids[value[1:]]
                    else:
                        for old, new in ids.items():
                            value = value.replace('url(#' + old + ')', 'url(#' + new + ')')
                    n.set(attr, value)
            node.set('x', str(x))
            node.set('y', str(y + (96 - size) / 2))
            node.set('width', str(size))
            node.set('height', str(size))
            sheet.append(node)
    label('Seven companion icons; application catalog and camera source are unchanged.', 24, 1060, 12, '#908caa')
    output = ET.tostring(sheet, encoding='unicode')
    write_file(REVIEWS / 'rose-punk-command-icons.svg', (output + '\n').encode())
    rasterize(output, 1100).save(REVIEWS / 'rose-punk-command-icons.png')
    assert hashlib.sha256(camera.read_bytes()).hexdigest() == camera_hash
    return REVIEWS / 'rose-punk-command-icons.png'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Render five sizes beside the unchanged camera')
    args = parser.parse_args()
    manifest = build()
    print(f'Built {len(manifest)} original Rose Punk command icons')
    if args.preview:
        print(preview(manifest))
