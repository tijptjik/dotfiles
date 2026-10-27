"""Camera-led material finish, using editable SVG paint rather than raster filters.

Flat tiles and identity geometry stay intact. Object illustrations can supply
purposeful detail layers; marks receive only a continuous pigment ramp.
"""
import colorsys
import re
import xml.etree.ElementTree as ET

SVG = 'http://www.w3.org/2000/svg'
PAINT = re.compile(r'^#[0-9a-fA-F]{6}$')


def mix(a, b, weight):
    aa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    bb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x * (1 - weight) + y * weight):02x}' for x, y in zip(aa, bb))


def source_pigment(match):
    """Retain source tonal modelling with a broader, coordinated pigment palette."""
    color = match.group()[1:]
    if len(color) == 3:
        color = ''.join(c * 2 for c in color)
    hue, sat, value = colorsys.rgb_to_hsv(*(int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    if sat < .12:
        return mix('#242338', '#f5ede1', value)
    # Desert amber, coral, jade, petrol, periwinkle, violet, and rose.
    pigments = ('#dd795f', '#e6ae62', '#a8b578', '#46b6a2', '#65b9c8', '#8596ed', '#b39bd9', '#df77ac')
    pigment = pigments[min(7, int(hue * 8))]
    if value < .72:
        return mix('#242338', pigment, value / .72)
    return mix(pigment, '#fff0d9', (value - .72) * .72)


def finish(text, key):
    """Shade fills in their own bounds, strokes in their containing SVG viewport.

    Explicit stroke coordinates keep horizontal/vertical line marks visible.
    No filters, duplicate silhouettes, global grain or shadows are introduced.
    """
    if key == 'camera':
        return text
    root = ET.fromstring(text)
    # Existing logo ramps also need the same warmer light and cooler underside.
    # Preserve their single silhouette and all internal apertures.
    for gradient in root.findall('./{*}defs/{*}linearGradient'):
        if gradient.get('id') in ('enamel', 'ink', 'gem') and len(gradient) >= 3:
            primary = gradient[1].get('stop-color')
            if primary and PAINT.fullmatch(primary):
                gradient[0].set('stop-color', mix(primary, '#fff0da', .55))
                gradient[2].set('stop-color', mix(primary, '#34304f', .38))
    serial = 0

    def viewport(scope):
        nonlocal serial
        defs = next((n for n in scope if n.tag == f'{{{SVG}}}defs'), None)
        if defs is None:
            defs = ET.Element(f'{{{SVG}}}defs')
            scope.insert(0, defs)
        bounds = [float(v) for v in scope.get('viewBox', '0 0 64 64').replace(',', ' ').split()]
        cache = {}

        def pigment(value, stroke):
            nonlocal serial
            if not PAINT.fullmatch(value):
                return value
            rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            if max(rgb) < .31:  # preserve apertures, ink, and negative spaces
                return value
            token = (value.lower(), stroke)
            if token in cache:
                return cache[token]
            serial += 1
            ident = f'material-{key}-{serial}'
            attrs = {'id': ident, 'x1': '0', 'y1': '0', 'x2': '.3', 'y2': '1'}
            if stroke:
                x, y, w, h = bounds
                attrs.update(gradientUnits='userSpaceOnUse', x1=str(x), y1=str(y), x2=str(x + w * .35), y2=str(y + h))
            gradient = ET.SubElement(defs, f'{{{SVG}}}linearGradient', attrs)
            neutral = max(rgb) - min(rgb) < .09
            high = mix(value, '#fff0da', .38 if not neutral else .13)
            shade_weight = .15 if key == 'spotify' else (.32 if not neutral else .18)
            low = mix(value, '#34304f', shade_weight)
            for offset, color in [('0', high), ('.32', value.lower()), ('1', low)]:
                ET.SubElement(gradient, f'{{{SVG}}}stop', {'offset': offset, 'stop-color': color})
            cache[token] = f'url(#{ident})'
            return cache[token]

        def walk(node):
            if node.tag == f'{{{SVG}}}svg':
                viewport(node)
                return
            if node.tag.rsplit('}', 1)[-1] in ('defs', 'title', 'desc', 'mask', 'clipPath') or node.get('id') == 'tile' or node.get('data-material') == 'authored':
                return
            for attr in ('fill', 'stroke'):
                if node.get(attr):
                    node.set(attr, pigment(node.get(attr), attr == 'stroke'))
            if node.get('style'):
                node.set('style', re.sub(r'(?<![\w-])(fill|stroke)\s*:\s*(#[\da-fA-F]{6})(?![\da-fA-F])',
                                        lambda m: m[1] + ':' + pigment(m[2], m[1] == 'stroke'), node.get('style')))
            for child in list(node):
                walk(child)
        for attr in ('fill', 'stroke'):
            if scope.get(attr):
                scope.set(attr, pigment(scope.get(attr), attr == 'stroke'))
        for child in list(scope):
            walk(child)
    viewport(root)
    return ET.tostring(root, encoding='unicode') + '\n'
