#!/usr/bin/env python3
"""Render workflow icon candidates at five sizes on dark and light surfaces."""
import hashlib
import json
import xml.etree.ElementTree as ET

from icon_data import HERE, PRIMARY, REVIEWS, write_file
from frameless import render

SVG = 'http://www.w3.org/2000/svg'
CANDIDATES = ('bitwarden', 'uv', 'fnm', 'gum', 'bun', 'bookmarks')


def scope_ids(node, prefix):
    """Keep each embedded SVG's paints and linked gradient definitions local."""
    ids = {n.get('id'): prefix + n.get('id') for n in node.iter() if n.get('id')}
    for n in node.iter():
        for attr, value in list(n.attrib.items()):
            if attr == 'id':
                value = ids[value]
            else:
                for old, new in ids.items():
                    value = value.replace(f'url(#{old})', f'url(#{new})')
                    if value == '#' + old:
                        value = '#' + new
            n.set(attr, value)


def main():
    catalog = json.loads((HERE / 'catalog.json').read_text())
    camera = PRIMARY / 'scalable/apps/camera.svg'
    camera_hash = hashlib.sha256(camera.read_bytes()).hexdigest()
    rows = [('Camera reference', camera)] + [(catalog[key]['name'],
            PRIMARY / f'scalable/apps/{key}.svg') for key in CANDIDATES]
    width, height = 1360, 920
    sheet = ET.Element(f'{{{SVG}}}svg', width=str(width), height=str(height), viewBox=f'0 0 {width} {height}')

    def text(value, x, y, size, fill):
        node = ET.SubElement(sheet, f'{{{SVG}}}text', x=str(x), y=str(y),
                             fill=fill, **{'font-family': 'sans-serif', 'font-size': str(size)})
        node.text = value

    for panel, surface, ink in [(0, '#191724', '#eee9e6'), (1, '#fffaf2', '#34304f')]:
        left = panel * 680
        ET.SubElement(sheet, f'{{{SVG}}}rect', x=str(left), width='680', height=str(height), fill=surface)
        text('Rose Punk · workflow review', left + 24, 36, 23, ink)
        text('4 revisions · Bitwarden and bookmarks approved · current camera', left + 24, 64, 12, ink)
        for size, x in [(24, 190), (32, 270), (48, 360), (64, 455), (96, 560)]:
            text(f'{size} px', left + x, 99, 12, ink)
        for index, (name, path) in enumerate(rows):
            y = 118 + index * 110
            text(name, left + 24, y + 50, 16, ink)
            if index and catalog[CANDIDATES[index-1]].get('reviewed'):
                text('Approved', left + 24, y + 69, 11, ink)
            for size, x in [(24, 190), (32, 270), (48, 360), (64, 455), (96, 560)]:
                node = ET.parse(path).getroot()
                prefix = f'p{panel}-r{index}-s{size}-'
                scope_ids(node, prefix)
                node.attrib.update(x=str(left + x), y=str(y + (96-size)/2), width=str(size), height=str(size))
                sheet.append(node)
        text('No release, deployment or framed approval.', left + 24, height-18, 13, ink)
    output = ET.tostring(sheet, encoding='unicode')
    destination = REVIEWS / 'rose-punk-workflow-candidates'
    write_file(destination.with_suffix('.svg'), (output+'\n').encode())
    # Render on a square viewport, then remove the unused transparent lower area.
    top = (width-height)//2
    render(output, width).crop((0, top, width, top+height)).save(destination.with_suffix('.png'))
    assert hashlib.sha256(camera.read_bytes()).hexdigest() == camera_hash
    print(destination.with_suffix('.png'))


if __name__ == '__main__':
    main()
