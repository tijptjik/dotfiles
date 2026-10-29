"""Compatibility imports; enrollment and context are owned by native Tjikup."""
import json
import os
from pathlib import Path
import subprocess

def profile_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'tjikup/device.json'

def profile():
    path = profile_path()
    return json.loads(path.read_text()) if path.exists() else None

def context(repo):
    binary = os.environ.get('TJIKUP_BINARY', 'tjikup')
    result = subprocess.run([binary, 'workflow', '--repo', str(repo), 'context'],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Native enrollment validation failed")
    return json.loads(result.stdout)

def configure(repo):
    context(repo)
