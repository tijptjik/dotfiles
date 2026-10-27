"""Shared optical sizing for the primary, transparent Rose Punk icons."""
import io
import math
import xml.etree.ElementTree as ET

SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
MEASURE_SIZE = 512


def render(text, size=MEASURE_SIZE):
    import cairo
    import gi
    gi.require_version('Rsvg', '2.0')
    from gi.repository import Rsvg
    from PIL import Image
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    viewport = Rsvg.Rectangle()
    viewport.x, viewport.y, viewport.width, viewport.height = 0, 0, size, size
    Rsvg.Handle.new_from_data(text.encode()).render_document(cairo.Context(surface), viewport)
    output = io.BytesIO()
    surface.write_to_png(output)
    return Image.open(io.BytesIO(output.getvalue())).convert('RGBA')


def without_tile(text):
    root = ET.fromstring(text)
    tiles = [(parent, child) for parent in root.iter() for child in parent
             if child.get('id') == 'tile']
    if len(tiles) != 1:
        raise ValueError(f'Expected one shared tile, found {len(tiles)}')
    parent, tile = tiles[0]
    parent.remove(tile)
    return root


def normalize(text):
    root = without_tile(text)
    alpha = render(ET.tostring(root, encoding='unicode')).getchannel('A')
    # Ignore only near-invisible antialias fringes when finding visible bounds.
    bounds = alpha.point(lambda a: 255 if a >= 8 else 0).getbbox()
    if not bounds:
        raise ValueError('Empty artwork')
    factor = MEASURE_SIZE / 64
    left, top, right, bottom = (v / factor for v in bounds)
    width, height = right - left, bottom - top
    area = sum(value * count / 255 for value, count in enumerate(alpha.histogram())) / factor**2
    # Dense objects need less extent than airy marks. Uniform scaling preserves
    # aspect ratios; 4 units of minimum margin protect strokes at small sizes.
    scale = min(56 / max(width, height),
                max(50 / max(width, height), math.sqrt(2200 / area)))
    tx = 32 - scale * (left + right) / 2
    ty = 32 - scale * (top + bottom) / 2
    group = ET.Element(f'{{{SVG}}}g', {
        'id': 'frameless-artwork',
        'transform': f'translate({tx:.6f} {ty:.6f}) scale({scale:.6f})'})
    for child in list(root):
        root.remove(child)
        group.append(child)
    root.append(group)
    output = ET.tostring(root, encoding='unicode') + '\n'
    # Alpha, including faint edge pixels, must stay clear of the canvas edge.
    visible = render(output).getchannel('A').getbbox()
    if not visible or min(visible[:2]) < factor * 3 or max(visible[2:]) > factor * 61:
        raise ValueError(f'Artwork approaches canvas edge: {visible}')
    return output, {'source_bounds': [left, top, right, bottom],
                    'alpha_area': round(area, 4), 'scale': round(scale, 6),
                    'translate': [round(tx, 6), round(ty, 6)],
                    'result_bounds': [round(v / factor, 3) for v in visible]}
