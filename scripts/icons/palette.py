#!/usr/bin/env python3
"""Shared palette and reference rendering for the managed icon theme."""
import colorsys
import copy
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from illustrated import icon as tile_icon

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / '.local/icon-reviews/docs/assets/icon-review'
THEME = ROOT / 'home/dot_local/share/icons/rose-punk/scalable/apps'
SVG = 'http://www.w3.org/2000/svg'
COLOR = r'#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![\w-])'
PAINT = ('fill', 'stroke', 'style', 'stop-color', 'flood-color', 'lighting-color')
ET.register_namespace('', SVG)


def apply_paint_overrides(text, overrides):
    """Resolve shared icon paint without changing source geometry or upstream files."""
    return re.sub(COLOR, lambda match: overrides.get(match.group().lower(), match.group()), text)


def load_palette():
    config = json.loads((HERE / 'palette.json').read_text())
    theme_path = ROOT / 'home/dot_config/vivid/themes/rose-punk.yml'
    colors = {k: '#' + v.lower() for k, v in re.findall(r'^  (base[0-9A-Fa-f]{2}): "([0-9A-Fa-f]{6})"', theme_path.read_text(), re.M)}
    colors = {token: config.get('paint_overrides', {}).get(value, value) for token, value in colors.items()}
    ramps = {name: [colors[token] for token in tokens] for name, tokens in config['families'].items()}
    assignments = {key: family for family, keys in config['assignments'].items() for key in keys}
    refs = {r['id']: r for r in json.loads((HERE / 'references/manifest.json').read_text())}
    for entry in refs.values():
        path = ROOT / entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Reference changed without provenance update: {path}')
    def family(key):
        if key == 'fedora':
            return 'blue'
        return assignments.get(key, 'blush')

    def recolor(text, name):
        """Keep tile paint intact; map symbol paint to the finite theme palette."""
        root = ET.fromstring(text)
        high, primary, shade, accent = ramps[name]
        def paint(match):
            value = match.group().lower()
            if len(value) == 4:
                value = '#' + ''.join(c * 2 for c in value[1:])
            rgb = [int(value[i:i+2], 16) / 255 for i in (1, 3, 5)]
            _, sat, light = colorsys.rgb_to_hsv(*rgb)
            if light < .36:
                return colors['base02']
            if light > .90 and sat < .26:
                return high
            if rgb[2] > rgb[0] * 1.02:
                return accent
            if light < .60:
                return shade
            return primary if sat > .25 else high

        # The common flat tile is identified independently of symbol geometry.
        # In identity icons, add that same tile around the existing geometry.
        if not any(n.get('id') == 'tile' for n in root.iter()):
            base = ET.fromstring(tile_icon('review', ''))
            for node in list(root):
                if node.tag.rsplit('}', 1)[-1] not in ('title', 'desc', 'defs'):
                    base.append(node)
            root = base
        for gradient in root.iter():
            ident = gradient.get('id')
            if ident in ('enamel', 'ink', 'gem'):
                ramp = [high, primary, shade] if ident != 'gem' else [colors['base07'], accent, shade]
                for node, value in zip(list(gradient), ramp):
                    node.set('stop-color', value)
        for child in list(root):
            kind = child.tag.rsplit('}', 1)[-1]
            if kind == 'defs':
                for definition in child:
                    if definition.get('id') not in ('tile', 'enamel', 'ink', 'gem'):
                        for node in definition.iter():
                            if node.text:
                                node.text = re.sub(COLOR, paint, node.text)
                            for attr, value in list(node.attrib.items()):
                                if attr in PAINT:
                                    node.set(attr, re.sub(COLOR, paint, value))
                continue
            if child.get('id') == 'tile':
                continue
            for node in child.iter():
                if node.tag.rsplit('}', 1)[-1] == 'style' and node.text:
                    node.text = re.sub(COLOR, paint, node.text)
                for attr, value in list(node.attrib.items()):
                    if attr in PAINT:
                        node.set(attr, re.sub(COLOR, paint, value).replace('currentColor', primary))
        return ET.tostring(root, encoding='unicode') + '\n'

    def adapted(reference, name):
        root = ET.fromstring((ROOT / refs[reference]['path']).read_text())
        rules = {}
        for node in root.iter():
            if node.tag.rsplit('}', 1)[-1] == 'style' and node.text:
                for names, body in re.findall(r'([^{}]+)\{([^{}]+)\}', node.text):
                    for selector in names.split(','):
                        rules[selector.strip().lstrip('.')] = body.strip()
        for node in root.iter():
            declarations = [rules[c] for c in node.get('class', '').split() if c in rules]
            if declarations:
                node.set('style', ';'.join(declarations + [node.get('style', '')]))
            node.attrib.pop('class', None)
            for child in list(node):
                if child.tag.rsplit('}', 1)[-1] == 'style':
                    node.remove(child)
        for node in list(root):
            if node.tag.rsplit('}', 1)[-1] in ('metadata', 'title', 'desc'):
                root.remove(node)
            elif reference == 'tjikup-existing' and node.tag.rsplit('}', 1)[-1] == 'rect':
                root.remove(node)
        root.set('x', '10'); root.set('y', '9')
        root.set('width', '44'); root.set('height', '44')
        root.set('preserveAspectRatio', 'xMidYMid meet')
        root.attrib.pop('class', None)
        # Reference strokes remain strokes. Filled brand geometry keeps its silhouette.
        root.set('color', ramps[name][1])
        if refs[reference]['kind'] == 'brand':
            root.set('fill', 'url(#enamel)')
        for node in root.iter():
            for attr in ('fill', 'stroke'):
                value = node.get(attr)
                if value and value != 'none' and not value.startswith('url('):
                    node.set(attr, 'url(#enamel)' if attr == 'fill' else 'url(#ink)')
        content = ET.tostring(root, encoding='unicode')
        # Object-bounding-box gradients disappear on perfectly vertical strokes.
        # Give stroke paint explicit units in the reference's own coordinate system.
        _, _, view_width, view_height = root.get('viewBox', '0 0 24 24').split()
        base = tile_icon('review', '').replace(
            'id="ink" x1="0" y1="0" x2="1" y2="1"',
            f'id="ink" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{view_width}" y2="{view_height}"')
        return recolor(base.replace('</svg>', content + '</svg>'), name)

    return config, colors, ramps, refs, family, recolor, adapted
