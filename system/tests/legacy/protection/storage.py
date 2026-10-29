#!/usr/bin/env python3
"""Guard existing si storage; never partition, format, mount, or start services."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

CONFIG = Path('/etc/si-snapraid-maintenance/config.json')
BEGIN = '# BEGIN tjikup si array'
END = '# END tjikup si array'
LEGACY = {'/mnt/data/disk4', '/mnt/parity/disk1', '/mnt/data/disk52'}

def command(*args):
    return subprocess.check_output(args, text=True).strip()

def check_mounts(config, docker_only=False):
    mounts = config['mounts']
    if docker_only:
        mounts = {'/mnt/data/disk22': mounts['/mnt/data/disk22']}
    for path, uuid in mounts.items():
        actual = command('findmnt', '-rn', '-o', 'UUID,FSTYPE', '--mountpoint', path).split()
        if actual != [uuid, 'ext4']:
            raise RuntimeError(f'{path}: expected ext4 UUID {uuid}, found {actual}')
    if not docker_only:
        actual = command('findmnt', '-rn', '-o', 'FSTYPE', '--mountpoint', '/mnt/storage')
        if actual != 'fuse.mergerfs':
            raise RuntimeError('/mnt/storage is not a mounted mergerfs pool')

def render_fstab(original, config):
    mounts = config['mounts']
    kept = []
    inside = False
    seen = False
    for line in original.splitlines():
        if line == BEGIN:
            if inside or seen:
                raise ValueError('duplicate or nested managed block')
            inside = seen = True
            continue
        if line == END:
            if not inside:
                raise ValueError('unmatched managed block end')
            inside = False
            continue
        if inside:
            continue
        fields = line.split()
        if fields and not line.lstrip().startswith('#') and len(fields) >= 2:
            source, target = fields[:2]
            if target in mounts or target in LEGACY or target == '/mnt/storage' or source == '/mnt/data/disk22/swap':
                continue
            if target.startswith(('/mnt/data/', '/mnt/parity/')):
                raise ValueError(f'unrecognized array mount: {target}; review manually')
        kept.append(line)
    if inside:
        raise ValueError('unterminated managed block')
    data = [row[2] for row in config['layout'] if row[0] == 'data']
    block = [BEGIN]
    for path, uuid in mounts.items():
        block.append(f'UUID={uuid} {path} ext4 defaults,nofail 0 2')
    options = 'defaults,allow_other,minfreespace=1M,moveonenospc=true,cache.files=partial,dropcacheonclose=true,category.create=mfs,fsname=mergerfs'
    options += ''.join(',x-systemd.requires-mounts-for=' + p for p in data)
    block.append(f'{":".join(data)} /mnt/storage fuse.mergerfs {options} 0 0')
    block.append('/mnt/data/disk22/swap none swap defaults,nofail 0 0')
    block.append(END)
    return '\n'.join(kept).rstrip() + '\n\n' + '\n'.join(block) + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--check-docker', action='store_true')
    group.add_argument('--print-fstab', action='store_true')
    group.add_argument('--write-fstab', action='store_true')
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    if args.check or args.check_docker:
        check_mounts(config, args.check_docker)
        print('Expected storage is mounted.')
        return
    path = Path('/etc/fstab')
    original = path.read_text()
    rendered = render_fstab(original, config)
    if args.print_fstab:
        print(rendered, end='')
        return
    if os.geteuid() != 0:
        raise RuntimeError('--write-fstab requires root')
    # Verify identities even on a new host, before writing any configuration.
    for mount, uuid in config['mounts'].items():
        device = command('blkid', '-U', uuid)
        if not device or command('blkid', '-s', 'TYPE', '-o', 'value', device) != 'ext4':
            raise RuntimeError(f'{mount}: missing expected ext4 UUID {uuid}')
    if rendered == original:
        print('fstab already matches; no changes.')
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    shutil.copy2(path, str(path) + '.before-tjikup-' + stamp)
    temporary = path.with_name('fstab.tjikup.tmp')
    with temporary.open('x') as f:
        f.write(rendered)
        f.flush()
        os.fsync(f.fileno())
    shutil.copystat(path, temporary)
    os.replace(temporary, path)
    print('fstab updated with backup; no disks mounted and no services restarted.')

if __name__ == '__main__':
    main()
