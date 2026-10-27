#!/usr/bin/env python3
"""Generate simplified orthographic land centred on Hong Kong (requires Shapely).

Natural Earth 1:110m land is public domain. The SVG keeps its authored ocean and
play symbol; only the land paths are regenerated from the vendored coastlines.
"""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from shapely.geometry import Polygon, shape
from shapely import transform
import numpy as np

HERE = Path(__file__).resolve().parent
SVG = 'http://www.w3.org/2000/svg'
LON, LAT = 114.1694, 22.3193
RADIUS = 24


def project(lon, lat, z=None):
    delta = math.radians(lon - LON)
    phi, center = math.radians(lat), math.radians(LAT)
    east = math.cos(phi) * math.sin(delta)
    north = math.cos(center) * math.sin(phi) - math.sin(center) * math.cos(phi) * math.cos(delta)
    return 32 + RADIUS * east, 32 - RADIUS * north


def rounded_path(ring):
    points = list(ring.coords)[:-1]
    mid = lambda a, b: ((a[0]+b[0])/2, (a[1]+b[1])/2)
    start = mid(points[-1], points[0])
    result = [f'M{start[0]:.3f} {start[1]:.3f}']
    for i, point in enumerate(points):
        end = mid(point, points[(i+1) % len(points)])
        result.append(f'Q{point[0]:.3f} {point[1]:.3f} {end[0]:.3f} {end[1]:.3f}')
    return ''.join(result) + 'Z'


def main():
    raw = HERE / 'upstream/plex-natural-earth-land.geojson'
    source = HERE / 'local/plex.svg'
    # For a northern centre the visible hemisphere lies north of this horizon.
    # Clip in geographic space first to avoid projecting the hidden hemisphere.
    horizon = []
    for i in range(1441):
        lon = -180 + i / 4
        lat = math.degrees(math.atan(-math.cos(math.radians(lon-LON)) / math.tan(math.radians(LAT))))
        horizon.append((lon, lat))
    visible = Polygon(horizon + [(180, 90), (-180, 90)])
    root = ET.fromstring(source.read_text())
    land = root.find(".//*[@clip-path='url(#globe)']")
    for node in list(land):
        land.remove(node)
    count = 0
    for feature in json.loads(raw.read_text())['features']:
        coast = shape(feature['geometry']).segmentize(1).intersection(visible)
        pieces = list(coast.geoms) if hasattr(coast, 'geoms') else [coast]
        for piece in pieces:
            if piece.is_empty or piece.geom_type != 'Polygon':
                continue
            projected = transform(piece, lambda coords: np.asarray([project(lon, lat) for lon, lat in coords])).simplify(.12, preserve_topology=True)
            if projected.area < .12:
                continue
            d = rounded_path(projected.exterior)
            d += ''.join(rounded_path(hole) for hole in projected.interiors if Polygon(hole).area >= .12)
            ET.SubElement(land, f'{{{SVG}}}path', {'d': d, 'fill-rule': 'evenodd'})
            count += 1
    ET.register_namespace('', SVG)
    source.write_text(ET.tostring(root, encoding='unicode') + '\n')
    provenance = HERE / 'provenance.json'
    data = json.loads(provenance.read_text())
    data['plex']['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    data['plex']['design_note'] = 'Hong Kong-centred orthographic globe (114.1694 E, 22.3193 N), simplified Natural Earth land in Plex yellow and a centred ivory play triangle.'
    data['plex']['land_reference'] = {
        'source': 'https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson',
        'file': 'upstream/plex-natural-earth-land.geojson',
        'sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
        'license': 'Natural Earth public domain: https://www.naturalearthdata.com/about/terms-of-use/',
        'projection_center': [LON, LAT],
    }
    provenance.write_text(json.dumps(data, indent=2) + '\n')
    print(f'Wrote {count} visible land regions; Hong Kong projects to {project(LON, LAT)}')


if __name__ == '__main__':
    main()
