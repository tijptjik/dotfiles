"""Canonical paths, validated source inputs, aliases, and generated file handling."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIMARY = ROOT / 'native/home/files/.local/share/icons/rose-punk'
REVIEWS = ROOT / '.local/icon-reviews/docs'


def read_json(path):
    return json.loads(path.read_text())


def gallery_catalog(folder=None):
    """Describe application and shell originals, excluding launcher controls."""
    folder = HERE if folder is None else folder
    catalog = read_json(folder / 'catalog.json')
    companions = read_json(folder / 'command-icons.json')
    overlap = catalog.keys() & companions.keys()
    if overlap:
        raise ValueError('Duplicate gallery icon IDs: ' + ', '.join(sorted(overlap)))
    for key, entry in companions.items():
        if entry.get('role') != 'shell':
            continue
        catalog[key] = {'installed': False,
                        'availability': 'Shell',
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


def _native_tree(folder):
    """Find declared native ownership; never register a new theme implicitly."""
    sources = ROOT / 'native/home/files'
    if not folder.is_relative_to(sources):
        return None
    manifest = sources.parent / 'files.json'
    entries = read_json(manifest)
    destination = '{{ user.home }}/' + folder.relative_to(sources).as_posix()
    parents = [entry for entry in entries if entry['path'] == destination]
    if len(parents) != 1 or parents[0]['kind'] != 'directory':
        raise ValueError(f'Register native icon directory in {manifest}: {destination}')
    parent = parents[0]
    children = {}
    for entry in entries:
        prefix = destination + '/'
        if not entry['path'].startswith(prefix):
            continue
        name = entry['path'][len(prefix):]
        if '/' in name or not name.endswith('.svg'):
            continue
        if name in children or entry['kind'] not in ('file', 'symlink', 'absent'):
            raise ValueError(f'Conflicting native icon ownership: {entry["path"]}')
        if entry.get('when') != parent.get('when'):
            raise ValueError(f'Icon host condition differs from directory: {entry["path"]}')
        if entry['kind'] == 'file' and (
                entry.get('template') or entry['source'] !=
                (folder / name).relative_to(sources.parent).as_posix()):
            raise ValueError(f'Icon has a different source: {entry["path"]}')
        children[name] = entry
    return manifest, entries, parent, children


def _native_outputs(folder, outputs, tree):
    """Translate renderer aliases into manifest entries, never encoded files."""
    _, _, parent, children = tree
    files, desired = {}, {}
    for encoded, data in outputs.items():
        name = encoded.removeprefix('symlink_')
        if Path(name).name != name or not name.endswith('.svg') or name in desired:
            raise ValueError(f'Invalid or duplicate generated icon: {encoded}')
        entry = {'path': parent['path'] + '/' + name}
        if 'when' in parent:
            entry['when'] = parent['when']
        previous = children.get(name, {})
        for key in ('uid', 'gid', 'create_only', 'sensitive'):
            if key in previous:
                entry[key] = previous[key]
        if encoded.startswith('symlink_'):
            target = data.decode().strip()
            if target not in outputs or target.startswith('symlink_'):
                raise ValueError(f'Alias {name} has no generated original: {target}')
            entry.update(kind='symlink', target=target)
        else:
            files[name] = data
            entry.update(kind='file', source=(folder / name).relative_to(
                ROOT / 'native/home').as_posix(), mode=previous.get('mode', '0644'))
        desired[name] = entry
    return files, desired


def native_aliases(folder):
    """Read native aliases, retaining encoded-file support for legacy fixtures."""
    tree = _native_tree(folder)
    if tree is not None:
        return {name: entry['target'] for name, entry in tree[3].items()
                if entry['kind'] == 'symlink'}
    return {path.name.removeprefix('symlink_'): path.read_text().strip()
            for path in sorted(folder.glob('symlink_*.svg'))}


def generated_files(folder, outputs):
    """Physical generated artifacts for release receipts, including ownership."""
    tree = _native_tree(folder)
    if tree is None:
        return {folder / name: data for name, data in outputs.items()}
    files, _ = _native_outputs(folder, outputs, tree)
    return {**{folder / name: data for name, data in files.items()},
            tree[0]: tree[0].read_bytes()}


def _disk_differences(folder, outputs):
    actual = {p.name for p in folder.iterdir()} if folder.is_dir() else set()
    expected = set(outputs)
    return [f'missing: {name}' for name in sorted(expected - actual)] + [
        f'stale: {name}' for name in sorted(actual - expected)] + [
        f'changed: {name}' for name in sorted(actual & expected)
        if not (folder / name).is_file() or (folder / name).read_bytes() != outputs[name]]


def differences(folder, outputs):
    tree = _native_tree(folder)
    if tree is None:
        return _disk_differences(folder, outputs)
    files, desired = _native_outputs(folder, outputs, tree)
    actual = tree[3]
    issues = _disk_differences(folder, files)
    issues.extend(f'manifest changed or missing: {name}' for name, entry in sorted(desired.items())
                  if actual.get(name) != entry)
    issues.extend(f'manifest stale: {name}' for name, entry in sorted(actual.items())
                  if name not in desired and entry['kind'] != 'absent')
    return issues


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


def write_tree(folder, outputs, *, prune=True):
    """Update generated SVGs and native ownership; partial producers opt out of pruning."""
    tree = _native_tree(folder)
    if tree is not None:
        files, desired = _native_outputs(folder, outputs, tree)
        manifest, entries, parent, children = tree
        if prune:
            for name, entry in children.items():
                if name not in desired:
                    desired[name] = {key: value for key, value in entry.items()
                                     if key in ('path', 'when')}
                    desired[name]['kind'] = 'absent'
        replacements = {entry['path']: entry for entry in desired.values()}
        updated = [replacements.pop(entry['path'], entry) for entry in entries]
        updated.extend(replacements.values())
        for name, data in sorted(files.items()):
            write_file(folder / name, data)
        for path in folder.glob('*.svg'):
            if path.name not in files and (prune or path.name in outputs):
                path.unlink()
        if updated != entries:
            write_file(manifest, (json.dumps(updated, indent=2) + '\n').encode())
        return
    for name, data in sorted(outputs.items()):
        write_file(folder / name, data)
    for path in folder.glob('*.svg'):
        if prune and path.name not in outputs:
            path.unlink()
