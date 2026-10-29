"""Local enrollment policy and explicit native template context."""
import getpass
import json
import os
from pathlib import Path
import socket

ROLES = {'desktop', 'laptop', 'server'}
LEGACY = {'fi': 'desktop', 'li': 'laptop', 'si': 'server'}


def profile_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'tjikup/device.json'


def profile():
    path = profile_path()
    if not path.exists():
        return None
    value = json.loads(path.read_text())
    if (value.get('version') != 1 or value.get('hostname') != socket.gethostname()
            or value.get('role') not in ROLES or not isinstance(value.get('subscriptions'), list)
            or not all(isinstance(item, str) for item in value['subscriptions'])):
        raise RuntimeError('Invalid or foreign device profile; run tjikup new device --replace')
    return value


def context(repo):
    device = profile()
    host = socket.gethostname()
    role = device['role'] if device else LEGACY.get(host)
    if role not in ROLES:
        raise RuntimeError('Unknown device: enroll with tjikup new device first')
    subscriptions = set(device['subscriptions']) if device else set()
    if device:
        recipes = []
        aliases = {}
        for file in ('tjikup.json', 'tjikup/recipes.json', 'system/tjikup/recipes.json'):
            document = json.loads((repo / file).read_text())
            recipes.extend(document.get('recipes', []))
            if file == 'tjikup.json':
                aliases = document.get('subscription_aliases', {})
        # Match the runner's one-hop aliases without rewriting enrollment.
        subscriptions = {aliases.get(key, key) for key in subscriptions}
        available = {r['id']: r for r in recipes
                     if (not r.get('roles') or role in r['roles'])
                     and (not r.get('hosts') or host in r['hosts'])}
        if not subscriptions <= available.keys():
            raise RuntimeError('Unknown or unavailable recipe subscription')
        subscriptions.update(key for key, r in available.items() if not r.get('optional') and not r.get('part_of'))
        while True:
            before = set(subscriptions)
            subscriptions.update(key for key, r in available.items() if r.get('part_of') in subscriptions)
            for key in set(subscriptions):
                dependencies = set(available[key].get('needs', []))
                # Prerequisites are always handled by the runner, not file policy.
                dependencies = {key for key in dependencies if not key.startswith('require:')}
                if not dependencies <= available.keys():
                    raise RuntimeError('A subscription needs a recipe unavailable on this device')
                subscriptions.update(dependencies)
            if before == subscriptions:
                break
    return {'hostname': host, 'role': role, 'is_client': role in {'desktop', 'laptop'},
            'is_desktop': role == 'desktop', 'is_laptop': role == 'laptop',
            'is_server': role == 'server', 'enrolled': device is not None,
            'subscriptions': sorted(subscriptions), 'user': {'name': getpass.getuser(), 'home': str(Path.home())},
            'repo_dir': str(repo), 'home_source': str(repo / 'home'),
            'system_source': str(repo / 'system/etc'), 'os': 'linux', 'anthropic_model_provider': 'zai'}


def configure(repo):
    """Validate enrollment; native templates consume context directly."""
    context(repo)
