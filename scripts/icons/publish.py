"""Versioned icon releases and the static type.hk download registry."""
import html
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

import framed
import release
from icon_data import HERE, PRIMARY, ROOT, write_file


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def validate_version(version):
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?', version):
        raise ValueError('Use a release version such as 0.1.0 or 0.1.0-rc.1')


def cut(trees, files, output, version):
    """Explicit release action approves this snapshot for its framed derivative."""
    validate_version(version)
    destination = output / version
    if destination.exists():
        raise ValueError(f'Release already exists: {destination}; use a new version or publish the existing snapshot')
    release.check_outputs(trees, files)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.cut-', dir=output) as temporary:
        prepared = Path(temporary) / version
        manifest = release.package(trees, files, prepared)
        # Derive from the packaged, verified snapshot, including every alias.
        with zipfile.ZipFile(prepared / 'rose-punk.zip') as archive:
            primary = {name.removeprefix('rose-punk/'): archive.read(name) for name in archive.namelist()}
        secondary = {name: framed.frame(data) if name.startswith('scalable/apps/') else data
                     for name, data in primary.items()}
        secondary['index.theme'] = framed.INDEX.encode()
        write_file(prepared / 'rose-punk-framed.zip', release.theme_zip(secondary, 'rose-punk-framed'))
        catalog = json.loads((HERE / 'catalog.json').read_text())
        services = json.loads((HERE / 'homepage.json').read_text())
        import homepage
        gallery = []
        for key, entry in sorted({**services, **catalog}.items()):
            data = trees[PRIMARY / 'scalable/apps'].get(key + '.svg')
            if data is None:
                data = trees[homepage.DEST][key + '.svg']
            write_file(prepared / 'icons' / (key + '.svg'), data)
            gallery.append({'id': key, 'name': entry['name'],
                            'src': f'/rose-punk-releases/{version}/icons/{key}.svg'})
        write_file(prepared / 'gallery.json', encoded(gallery))
        manifest.update(version=version, source_commit=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            source_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
            framed={'approval': 'Explicit release cut', 'tile': framed.TILE,
                    'artwork_transform': framed.TRANSFORM})
        manifest['artifacts'] = {str(path.relative_to(prepared)): release.sha256(path.read_bytes())
                                 for path in sorted(prepared.rglob('*')) if path.is_file() and path.name != 'release.json'}
        write_file(prepared / 'release.json', encoded(manifest))
        checksums = {**manifest['artifacts'], 'release.json': release.sha256((prepared / 'release.json').read_bytes())}
        write_file(prepared / 'SHA256SUMS', ''.join(f'{digest}  {name}\n' for name, digest in sorted(checksums.items())).encode())
        prepared.rename(destination)
    return destination


def verify_snapshot(snapshot):
    manifest = json.loads((snapshot / 'release.json').read_text())
    validate_version(manifest['version'])
    for name, digest in manifest['artifacts'].items():
        path = snapshot / name
        if not path.resolve().is_relative_to(snapshot.resolve()) or release.sha256(path.read_bytes()) != digest:
            raise ValueError(f'Release artifact failed verification: {name}')
    for name in ('rose-punk.zip', 'rose-punk-framed.zip', 'gallery.json'):
        if name not in manifest['artifacts']:
            raise ValueError(f'Missing release artifact: {name}')
    return manifest


def register(snapshot, site):
    manifest = verify_snapshot(snapshot)
    if not (site / 'wrangler.jsonc').is_file() or not (site / 'src/lib/content').is_dir():
        raise ValueError(f'Not a type.hk checkout: {site}')
    resources_path = site / 'src/lib/content/rose-punk.ts'
    resources = resources_path.read_text()
    marker = 'export const rosePunkResources: ThemeResource[] = ['
    if marker not in resources:
        raise ValueError('Cannot locate the type.hk theme resource list')
    if "href: '/rose-punk-releases/'" not in resources:
        resources = resources.replace(marker, marker + "\n  { label: 'Icon releases', href: '/rose-punk-releases/' },", 1)
    registry_dir = site / 'public/rose-punk-releases'
    registry_path = registry_dir / 'registry.json'
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {'schema': 1, 'releases': []}
    version = manifest['version']
    target = registry_dir / version
    # Never silently replace a published version; identical retry is safe.
    if target.exists():
        verify_snapshot(target)
        if (target / 'release.json').read_bytes() != (snapshot / 'release.json').read_bytes():
            raise ValueError(f'Published version {version} differs; choose a new version')
    else:
        registry_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.register-', dir=registry_dir) as temporary:
            staging = Path(temporary) / version
            shutil.copytree(snapshot, staging)
            staging.rename(target)
    entry = {'version': version, 'manifest': f'/rose-punk-releases/{version}/release.json',
             'sha256': release.sha256((snapshot / 'release.json').read_bytes()),
             'downloads': {name: f'/rose-punk-releases/{version}/{name}' for name in ('rose-punk.zip', 'rose-punk-framed.zip', 'SHA256SUMS')}}
    registry['releases'] = [entry] + [item for item in registry['releases'] if item['version'] != version]
    registry['latest'] = version
    write_file(resources_path, resources.encode())
    write_file(registry_path, encoded(registry))
    write_file(site / 'src/lib/content/rose-punk-icons.json', (snapshot / 'gallery.json').read_bytes())
    rows = ''.join('<li><strong>' + html.escape(item['version']) + '</strong> ' + ' · '.join(
        f'<a href="{html.escape(url)}">{html.escape(name)}</a>' for name, url in item['downloads'].items()) + '</li>' for item in registry['releases'])
    write_file(registry_dir / 'index.html', ('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Rose Punk releases</title>'
        '<style>body{background:#26233a;color:#eee9e6;font:18px system-ui;max-width:60rem;margin:4rem auto;padding:1rem}'
        'a{color:#9bdfeb}li{margin:1.5rem 0}</style><h1>Rose Punk releases</h1>'
        '<p>Install either ZIP in ~/.local/share/icons. Each includes app aliases and attribution.</p>'
        '<p><a href="/themes/rose-punk#icons">Icon gallery</a> · <a href="registry.json">Release registry</a></p>'
        '<ul>' + rows + '</ul></html>').encode())


def deploy(snapshot, site):
    """Use the site's existing build/deploy contract; verify actual public bytes."""
    manifest = verify_snapshot(snapshot)
    pending = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=site, text=True)
    allowed = ('public/rose-punk-releases/', 'src/lib/content/rose-punk-icons.json', 'src/lib/content/rose-punk.ts')
    unrelated = [line[3:] for line in pending.splitlines() if not line[3:].startswith(allowed)]
    if unrelated:
        raise ValueError('Commit or isolate unrelated type.hk changes before deployment:\n' + '\n'.join(unrelated))
    subprocess.run(['bun', 'run', 'check'], cwd=site, check=True)
    subprocess.run(['bun', 'run', 'deploy'], cwd=site, check=True)
    prefix = f'https://type.hk/rose-punk-releases/{manifest["version"]}/'
    # These downloads prove both variants and the exact manifest reached the origin.
    for name in ('release.json', 'rose-punk.zip', 'rose-punk-framed.zip'):
        with urllib.request.urlopen(prefix + name, timeout=60) as response:
            if release.sha256(response.read()) != release.sha256((snapshot / name).read_bytes()):
                raise ValueError(f'Deployment verification failed: {prefix}{name}')
    with urllib.request.urlopen('https://type.hk/rose-punk-releases/registry.json', timeout=60) as response:
        registry = json.load(response)
        if registry['latest'] != manifest['version']:
            raise ValueError('Public registry does not point to this release')
    write_file(snapshot.parent / (manifest['version'] + '-deployment.json'), encoded(
        {'version': manifest['version'], 'verified_url': prefix,
         'manifest_sha256': release.sha256((snapshot / 'release.json').read_bytes())}))
