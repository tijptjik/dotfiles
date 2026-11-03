"""Load approved, already sized SVG originals without repainting or rescaling."""
import re
import xml.etree.ElementTree as ET

from icon_data import verify_source


def read_svg(relative, expected):
    data = verify_source(relative, expected).read_bytes()
    root = ET.fromstring(data)
    if root.get('viewBox') != '0 0 64 64':
        raise ValueError(f'Reviewed artwork needs a 64-unit viewBox: {relative}')
    ids = [n.get('id') for n in root.iter() if n.get('id')]
    if len(ids) != len(set(ids)) or 'tile' in ids:
        raise ValueError(f'Duplicate IDs or shared tile in reviewed artwork: {relative}')
    for node in root.iter():
        if node.tag.split('}')[-1] in {'script', 'image', 'text', 'foreignObject'}:
            raise ValueError(f'Non-vector content in reviewed artwork: {relative}')
        for attr, value in node.attrib.items():
            attr = attr.split('}')[-1]
            if attr.lower().startswith('on'):
                raise ValueError(f'Event handler in reviewed artwork: {relative}')
            if attr in {'href', 'src'} and (not value.startswith('#') or value[1:] not in ids):
                raise ValueError(f'External or missing reference in reviewed artwork: {relative}')
            for target in re.findall(r'url\(([^)]+)\)', value):
                if not target.startswith('#') or target[1:] not in ids:
                    raise ValueError(f'External or missing paint in reviewed artwork: {relative}')
    return data
