#!/usr/bin/env python3
"""Local package presence checks and explicit install/update dispatch."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from device_policy import context

ROOT = Path(__file__).resolve().parents[1]


def test(item, installed_rpms=None):
    if 'plugin' in item:
        root = Path.home() / '.config/herdr/plugins'
        # Installed plugin directories use plugin-id plus a content hash.
        return any(path.is_file() for path in root.glob('github/' + item['plugin'] + '-*/herdr-plugin.toml'))
    if 'not' in item:
        return not test(item['not'], installed_rpms)
    if 'any' in item:
        return any(test(value, installed_rpms) for value in item['any'])
    if 'command' in item:
        return shutil.which(item['command']) is not None
    if 'executable' in item:
        path = Path(item['executable']).expanduser()
        return path.is_file() and os.access(path, os.X_OK)
    if 'path' in item:
        return Path(item['path']).expanduser().exists()
    if 'rpm' in item:
        if installed_rpms is not None:
            return item['rpm'] in installed_rpms
        return subprocess.run(['rpm', '-q', item['rpm']], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=15).returncode == 0
    if 'flatpak' in item:
        if not shutil.which('flatpak'):
            return False
        return subprocess.run(['flatpak', 'info', '--system', item['flatpak']],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15).returncode == 0
    raise ValueError('Unknown package presence check')


def presence(key, role):
    policy = json.loads((ROOT / 'tjikup/package-checks.json').read_text())[key]
    if policy.get('roles') and role not in policy['roles']:
        return None
    checks = list(policy.get('checks', []))
    for plugin in policy.get('plugins', []):
        checks.append({'plugin': plugin})
    if ecosystem := policy.get('packages'):
        packages = json.loads((ROOT / 'native/tasks/data.json').read_text())['packages']
        for group in ('common', 'server' if role == 'server' else 'client'):
            values = packages.get(group, {}).get(ecosystem, [])
            buckets = values.values() if isinstance(values, dict) else [values]
            for names in buckets:
                # An empty YAML repository list becomes JSON null. It is an
                # empty selection, not an error and not a package to install.
                if names is None:
                    continue
                if not isinstance(names, list) or not all(isinstance(name, str) and name for name in names):
                    raise ValueError(f'Invalid {ecosystem} package list in {group}')
                checks.extend({ecosystem: name} for name in names)
    # One fresh RPM database read per presence check, not one process per package.
    # No persistent cache: external dnf/rpm changes are visible on the next run.
    installed_rpms = None
    if policy.get('packages') == 'rpm':
        result = subprocess.run(['rpm', '-qa', '--qf', '%{NAME}\n'], capture_output=True,
                                text=True, check=True, timeout=30)
        installed_rpms = set(result.stdout.splitlines())
    return [test(item, installed_rpms) for item in checks]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'skip-update', 'run'])
    parser.add_argument('package')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    values = presence(args.package, context(ROOT)['role'])
    ready = values is None or all(values)
    if args.package == 'python' and values is not None and ready and (args.action == 'check' or os.environ.get('TJIKUP_OPERATION') == 'install'):
        ready = subprocess.run(['uv', 'sync', '--check', '--offline', '--project',
                                str(Path.home() / '.local/share/pytjik'), '--python', '3.13',
                                '--no-python-downloads'], env={**os.environ, 'UV_PROJECT_ENVIRONMENT': str(Path.home() / '.venv')},
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30).returncode == 0
    if args.action == 'check':
        return 0 if ready else 1
    if args.action == 'skip-update':
        return 0 if values is None or not any(values) else 1
    operation = os.environ.get('TJIKUP_OPERATION', 'install')
    if operation not in {'install', 'update'}:
        parser.error('package dispatch requires an install or update recipe')
    if values is None or (operation == 'install' and ready) or (operation == 'update' and not any(values)):
        print(f'SKIP    ✓ {args.package}  ' + ('already installed' if operation == 'install' else 'not installed'))
        return 0
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('run requires a command after --')
    return subprocess.call(command)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Package presence check failed: {error}', file=sys.stderr)
        raise SystemExit(2)
