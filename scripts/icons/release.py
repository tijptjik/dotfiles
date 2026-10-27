#!/usr/bin/env python3
"""Build, verify, or package Rose Punk offline without installing or approving it."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import zipfile
import zlib

from icon_data import HERE, PRIMARY, ROOT, differences, write_file, write_tree

RELEASES = ROOT / '.local/icon-releases'


def generated_outputs():
    # Rendering imports stay here so --help works without optional build dependencies.
    import fleet
    import fullset
    import homepage
    icons, aliases = fullset.render()
    sprites = fleet.render(icons)
    services = homepage.render()
    return {
        PRIMARY / 'scalable/apps': icons,
        homepage.DEST: services,
    }, {
        HERE / 'theme-aliases.json': (json.dumps(aliases, indent=2, sort_keys=True) + '\n').encode(),
        ROOT / 'scripts/fleet_update/icons32.json': sprites,
    }


def check_outputs(trees, files):
    issues = [f'{folder.relative_to(ROOT)}: {issue}'
              for folder, outputs in trees.items() for issue in differences(folder, outputs)]
    issues.extend(f'{path.relative_to(ROOT)}: changed or missing'
                  for path, data in files.items() if not path.is_file() or path.read_bytes() != data)
    if issues:
        raise ValueError('Generated outputs are stale; run release.py build:\n' + '\n'.join(issues))


def theme_files(icons):
    """Materialize Chezmoi aliases as regular SVGs in the installable download."""
    files = {'index.theme': (PRIMARY / 'index.theme').read_bytes()}
    for name, data in icons.items():
        if name.startswith('symlink_'):
            files['scalable/apps/' + name.removeprefix('symlink_')] = icons[data.decode().strip()]
        else:
            files['scalable/apps/' + name] = data
    return files


def theme_zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo('rose-punk/' + name, (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def environment():
    import cairo
    import gi
    import PIL
    gi.require_version('Rsvg', '2.0')
    from gi.repository import Rsvg
    return {'python': platform.python_version(), 'pillow': PIL.__version__,
            'cairo': cairo.cairo_version_string(),
            'librsvg': f'{Rsvg.MAJOR_VERSION}.{Rsvg.MINOR_VERSION}.{Rsvg.MICRO_VERSION}',
            'imagemagick': subprocess.check_output(['magick', '-version'], text=True).splitlines()[0],
            'zlib': zlib.ZLIB_RUNTIME_VERSION}


def package(trees, files, destination):
    check_outputs(trees, files)
    payload = theme_files(trees[PRIMARY / 'scalable/apps'])
    for name in ('catalog.json', 'provenance.json'):
        payload['attribution/' + name] = (HERE / name).read_bytes()
    for folder in ('upstream', 'references'):
        for path in (HERE / folder).iterdir():
            if path.is_file() and 'license' in path.name.lower():
                payload[f'attribution/{folder}/{path.name}'] = path.read_bytes()
    payload['NOTICE.txt'] = (
        'Rose Punk is an unofficial icon theme. Application names and marks remain\n'
        'with their owners. Attribution, source URLs and license declarations are\n'
        'in attribution/provenance.json; vendored license texts accompany it.\n').encode()
    download = theme_zip(payload)
    inputs = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    inputs += [ROOT / 'home/dot_config/vivid/themes/rose-punk.yml',
               ROOT / 'scripts/fleet_update/icon_catalog.py', PRIMARY / 'index.theme']
    generated = {**files, **{folder / name: data for folder, outputs in trees.items()
                             for name, data in outputs.items()}}
    manifest = {'schema': 1, 'theme': 'rose-punk', 'environment': environment(),
                'archive': {'file': 'rose-punk.zip', 'sha256': sha256(download)},
                'inputs': {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in sorted(inputs)},
                'outputs': {str(p.relative_to(ROOT)): sha256(data) for p, data in sorted(generated.items())}}
    write_file(destination / 'rose-punk.zip', download)
    write_file(destination / 'release.json', (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode())
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'build', 'package'), nargs='?', default='check')
    parser.add_argument('--output', type=Path, default=RELEASES, help='package output directory')
    args = parser.parse_args()
    try:
        trees, files = generated_outputs()
        if args.action == 'build':
            # Every input and producer has succeeded before any tracked output changes.
            for folder, outputs in trees.items():
                write_tree(folder, outputs)
            for path, data in files.items():
                write_file(path, data)
        elif args.action == 'package':
            package(trees, files, args.output)
        else:
            check_outputs(trees, files)
    except (ValueError, OSError, ImportError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')
    print({'check': 'All desktop, fleet, and Homepage outputs match their sources.',
           'build': 'Built desktop, fleet, and Homepage outputs; no deployment or approval.',
           'package': f'Wrote rose-punk.zip and release.json to {args.output}.'}[args.action])


if __name__ == '__main__':
    main()
