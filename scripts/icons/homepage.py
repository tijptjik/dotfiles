#!/usr/bin/env python3
"""Build frameless Si service SVGs offline; never deploy them.

All inputs are editable source SVGs and the hash/attribution manifest beside
this script. Optional visual reviews belong under ignored .local/icon-reviews/.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DEST = ROOT / 'native/home/files/dockers/homepage/images/rose-punk'
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
_spec = importlib.util.spec_from_file_location('homepage_frameless', HERE / 'frameless.py')
frameless = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(frameless)


def artwork(entry):
    source = HERE / entry['geometry']
    if hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
        raise ValueError(f'Changed source without provenance update: {source}')
    root = ET.parse(source).getroot()
    tile = ET.Element(f'{{{SVG}}}rect', {'id': 'tile', 'x': '3', 'y': '2', 'width': '58', 'height': '58',
        'rx': '17', 'fill': '#26233a', 'stroke': '#555169', 'stroke-opacity': '.45', 'stroke-width': '.65'})
    root.insert(0, tile)
    output = frameless.normalize(ET.tostring(root, encoding='unicode'))[0]
    return '\n'.join(line.rstrip() for line in output.splitlines()) + '\n'


def render():
    manifest = json.loads((HERE / 'homepage.json').read_text())
    # Validate and render every source before updating the served SVGs.
    outputs = {key: artwork(entry) for key, entry in manifest.items()}
    inventory = ROOT / 'scripts/icons/docker-services.json'
    if inventory.is_file():
        for key, entry in json.loads(inventory.read_text()).items():
            outputs[key] = outputs[entry['icon']]
    return {f'{key}.svg': text.encode() for key, text in outputs.items()}


def main():
    outputs = render()
    from icon_data import write_tree
    write_tree(DEST, outputs)
    print(f'Built {len(outputs)} Homepage icons; no review assets or deployment')


if __name__ == '__main__':
    main()
