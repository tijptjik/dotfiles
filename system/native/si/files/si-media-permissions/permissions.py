#!/usr/bin/env python3
"""Maintain shared media access on si; never scan appData or private storage."""
import argparse
import base64
import collections
import datetime
import fcntl
import grp
import json
import os
from pathlib import Path
import socket
import stat
import sys

HERE = Path(__file__).resolve().parent
STATE = Path('/var/lib/si-media-permissions')
ALLOWED = {'public/movies', 'public/shows', 'meta/downloads/radarr', 'meta/downloads/sonarr'}
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def desired(current, gid):
    mode = stat.S_IMODE(current.st_mode)
    if stat.S_ISDIR(current.st_mode):
        return gid, mode | 0o2070  # group rwx + inheritance; preserve owner/other bits
    if stat.S_ISREG(current.st_mode):
        return gid, mode | 0o060  # group rw; never add executable/world access
    return current.st_gid, mode


def open_root(mount, relative):
    """Anchor every path component to directory FDs; reject symlink ancestors."""
    fd = os.open(mount, DIR_FLAGS)
    try:
        for name in Path(relative).parts:
            next_fd = os.open(name, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


class Journal:
    def __init__(self, state):
        self.state = state
        self.path = None
        self.handle = None

    def record(self, path, current, fd):
        if self.handle is None:
            self.state.mkdir(mode=0o700, parents=True, exist_ok=True)
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            self.path = self.state / ('changes-' + stamp + '.jsonl')
            self.handle = self.path.open('x')
            self.path.chmod(0o600)
        record = {'path': str(path), 'uid': current.st_uid, 'gid': current.st_gid,
                  'mode': stat.S_IMODE(current.st_mode), 'device': current.st_dev,
                  'inode': current.st_ino, 'size': current.st_size,
                  'mtimeNs': current.st_mtime_ns}
        for attribute in ('system.posix_acl_access', 'system.posix_acl_default'):
            try:
                record[attribute] = base64.b64encode(os.getxattr(fd, attribute)).decode()
            except OSError as error:
                if error.errno not in (61, 95):  # ENODATA / ENOTSUP
                    raise
        self.handle.write(json.dumps(record) + '\n')
        self.handle.flush()  # record before changing each inode

    def close(self):
        if self.handle:
            os.fsync(self.handle.fileno())
            self.handle.close()


def scan_root(root, root_fd, gid, apply=False, journal=None):
    counts = collections.Counter()
    device = os.fstat(root_fd).st_dev

    def update(fd, path):
        current = os.fstat(fd)
        if current.st_dev != device:
            raise RuntimeError('Nested filesystem refused: ' + str(path))
        if not (stat.S_ISDIR(current.st_mode) or stat.S_ISREG(current.st_mode)):
            counts['skippedSpecial'] += 1
            return
        kind = 'directories' if stat.S_ISDIR(current.st_mode) else 'files'
        counts[kind] += 1
        target_gid, target_mode = desired(current, gid)
        if (current.st_gid, stat.S_IMODE(current.st_mode)) == (target_gid, target_mode):
            return
        counts['changed'] += 1
        counts['changedDirectories' if kind == 'directories' else 'changedFiles'] += 1
        if apply:
            journal.record(path, current, fd)
            if current.st_gid != target_gid:
                os.fchown(fd, -1, target_gid)
            os.fchmod(fd, target_mode)
            after = os.fstat(fd)
            # Downloads/imports remain active and may change size/mtime themselves.
            if (after.st_uid, after.st_gid, stat.S_IMODE(after.st_mode)) != (current.st_uid, target_gid, target_mode):
                raise RuntimeError('Permission verification failed: ' + str(path))

    def walk_error(error):
        raise error

    for relative, directories, files, directory_fd in os.fwalk('.', dir_fd=root_fd, follow_symlinks=False, onerror=walk_error):
        path = root / relative
        update(directory_fd, path)
        for name in files:
            try:
                current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if not stat.S_ISREG(current.st_mode):
                    counts['skippedSpecial'] += 1
                    continue
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory_fd)
                try:
                    update(fd, path / name)
                finally:
                    os.close(fd)
            except FileNotFoundError:
                counts['vanishedDuringScan'] += 1  # normal imports can move a file
    return counts


def guarded_scan(policy, config, apply=False, state=STATE):
    if policy['gid'] != 950 or policy['group'] != 'media' or set(policy['roots']) != ALLOWED:
        raise RuntimeError('Unexpected media permission scope or identity')
    if grp.getgrnam('media').gr_gid != policy['gid']:
        raise RuntimeError('media group identity changed')
    sys.path.insert(0, '/etc/si-provision')
    from storage import check_mounts
    check_mounts(config)
    mounts = [Path(row[2]) for row in config['layout'] if row[0] == 'data']
    counts = collections.Counter()
    seen = set()
    journal = Journal(state)
    opened = []
    try:
        for mount in mounts:
            for relative in policy['roots']:
                root = mount / relative
                try:
                    fd = open_root(mount, relative)
                except FileNotFoundError:
                    continue
                if os.fstat(fd).st_dev != mount.stat().st_dev:
                    os.close(fd)
                    raise RuntimeError('Nested filesystem refused: ' + str(root))
                seen.add(relative)
                opened.append((root, fd))
        if seen != ALLOWED:
            raise RuntimeError('Missing media roots: ' + ', '.join(sorted(ALLOWED - seen)))
        for root, fd in opened:
            counts.update(scan_root(root, fd, policy['gid'], apply, journal))
    finally:
        journal.close()
        for root, fd in opened:
            os.close(fd)
    result = dict(counts, apply=apply, completedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(), journal=str(journal.path) if journal.path else None)
    if apply:
        state.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = state / 'last-success.tmp'
        temporary.write_text(json.dumps(result, indent=2) + '\n')
        temporary.replace(state / 'last-success.json')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='otherwise audit without changing permissions')
    args = parser.parse_args()
    if socket.gethostname().split('.')[0] != 'si' or os.geteuid() != 0:
        parser.error('Run as root on si')
    os.umask(0o077)
    with open('/run/lock/si-snapraid-maintenance.lock', 'a') as maintenance_lock:
        try:
            fcntl.flock(maintenance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Media permissions deferred: parity maintenance is running.')
            return 75
        with open('/run/lock/si-app-backup.lock', 'a') as backup_lock:
            try:
                fcntl.flock(backup_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print('Media permissions deferred: application backup is running.')
                return 75
            config = json.loads(Path('/etc/si-snapraid-maintenance/config.json').read_text())
            policy = json.loads((HERE / 'policy.json').read_text())
            print(json.dumps(guarded_scan(policy, config, args.apply), indent=2), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
