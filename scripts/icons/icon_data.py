"""Canonical paths, validated source inputs, aliases, and generated file handling."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIMARY = ROOT / 'home/dot_local/share/icons/rose-punk'
REVIEWS = ROOT / '.local/icon-reviews/docs'


def read_json(path):
    return json.loads(path.read_text())


def gallery_catalog(folder=None):
    """Describe every primary original, including shell and command companions."""
    folder = HERE if folder is None else folder
    catalog = read_json(folder / 'catalog.json')
    companions = read_json(folder / 'command-icons.json')
    overlap = catalog.keys() & companions.keys()
    if overlap:
        raise ValueError('Duplicate gallery icon IDs: ' + ', '.join(sorted(overlap)))
    for key, entry in companions.items():
        catalog[key] = {'installed': False,
                        'availability': 'Shell' if entry.get('role') == 'shell' else 'Launcher control',
                        **entry}
    return catalog


def source_file(relative):
    path = (HERE / relative).resolve()
    if not path.is_relative_to(HERE) or not path.is_file():
        raise ValueError(f'Missing or invalid icon source: {relative}')
    return path


def verify_source(relative, expected):
    path = source_file(relative)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f'Source changed without provenance update: {relative}')
    return path


def load_catalog():
    catalog = read_json(HERE / 'catalog.json')
    provenance = read_json(HERE / 'provenance.json')
    retired = read_json(HERE / 'retired.json')
    if set(catalog) & set(retired):
        raise ValueError('Retired icons must not appear in the active catalog')
    for key, entry in catalog.items():
        if key in ('.', '..') or Path(key).name != key or any(c.isspace() for c in key):
            raise ValueError(f'Invalid icon key: {key}')
        if key not in provenance:
            raise ValueError(f'Missing provenance: {key}')
        if 'geometry' in entry:
            verify_source(entry['geometry'], provenance[key]['sha256'])
    return catalog


def aliases_for(catalog):
    """Derive aliases from source declarations, never from yesterday's output."""
    aliases = {}
    def add(name, key):
        if not name or '/' in name or any(c.isspace() for c in name):
            return  # Upstream metadata can contain absolute paths and display names.
        if name in ('.', '..'):
            raise ValueError(f'Invalid alias: {name}')
        if name in aliases and aliases[name] != key:
            raise ValueError(f'Conflicting alias {name}: {aliases[name]} and {key}')
        if name in catalog and name != key:
            raise ValueError(f'Alias {name} would shadow another catalog original')
        aliases[name] = key
    for key, entry in catalog.items():
        for name in entry['icon_names']:
            name = name.removesuffix('.svg').removesuffix('.png')
            if not name.startswith('rose-punk-'):
                add(name, key)
        for desktop in entry['desktop_ids']:
            add(desktop.removesuffix('.desktop'), key)
    for name, key in read_json(HERE / 'alias-overrides.json').items():
        if key not in catalog:
            raise ValueError(f'Alias {name} targets a missing icon: {key}')
        add(name, key)
    return dict(sorted(aliases.items()))


def differences(folder, outputs):
    actual = {p.name for p in folder.iterdir()} if folder.is_dir() else set()
    expected = set(outputs)
    return [f'missing: {name}' for name in sorted(expected - actual)] + [
        f'stale: {name}' for name in sorted(actual - expected)] + [
        f'changed: {name}' for name in sorted(actual & expected)
        if not (folder / name).is_file() or (folder / name).read_bytes() != outputs[name]]


def write_file(path, data):
    """Replace one generated file without exposing partially written bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_tree(folder, outputs):
    """Update an exclusively generated SVG folder and retire stale SVGs."""
    for name, data in sorted(outputs.items()):
        write_file(folder / name, data)
    for path in folder.glob('*.svg'):
        if path.name not in outputs:
            path.unlink()
