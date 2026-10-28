#!/usr/bin/python3
"""Daily, label-scoped Transmission cleanup on si. Defaults to dry-run."""
import argparse
import base64
from collections import Counter
import datetime
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

LABELS = {'sonarr', 'radarr', 'sonarred', 'radarred'}
IPT_HOSTS = {'localhost.stackoverflow.tech', 'routing.bgp.technology', 'ssl.empirehost.me'}
MIN_SEED_SECONDS = 15 * 24 * 60 * 60
STATE = Path('/var/lib/si-transmission-cleanup')
DOWNLOADS = Path('/mnt/storage/meta/downloads')
FIELDS = ['hashString', 'name', 'labels', 'metadataPercentComplete', 'percentDone',
          'leftUntilDone', 'totalSize', 'files', 'downloadDir', 'secondsSeeding',
          'isPrivate', 'trackers']


def tracker_kind(torrent):
    """Unknown/missing tracker metadata must never take the public shortcut."""
    hosts = []
    for tracker in torrent.get('trackers', []):
        try:
            url = urllib.parse.urlsplit(tracker['announce'])
            if url.scheme not in {'http', 'https', 'udp'} or not url.hostname:
                return 'unknown'
            hosts.append(url.hostname.lower().rstrip('.'))
        except (KeyError, ValueError, TypeError):
            return 'unknown'
    if not hosts:
        return 'unknown'
    if any(h in IPT_HOSTS or h == 'iptorrents.com' or h.endswith('.iptorrents.com')
           or h == 'iptorrents.me' or h.endswith('.iptorrents.me') for h in hosts):
        return 'ipt'
    return 'public' if torrent.get('isPrivate') is False else 'unknown'


def decision(torrent):
    if not LABELS.intersection(torrent.get('labels', [])):
        return False, 'unmanaged-label'
    files = torrent.get('files', [])
    if (torrent.get('metadataPercentComplete') != 1 or torrent.get('percentDone') != 1
            or torrent.get('leftUntilDone') != 0 or torrent.get('totalSize', 0) <= 0
            or not files or any(f.get('bytesCompleted', -1) != f.get('length') for f in files)):
        return False, 'incomplete'
    kind = tracker_kind(torrent)
    if kind == 'unknown':
        return False, 'unknown-tracker'
    if kind == 'ipt':
        seconds = torrent.get('secondsSeeding')
        if not isinstance(seconds, (int, float)) or not seconds > MIN_SEED_SECONDS:
            return False, 'ipt-under-two-weeks'
    return True, kind


def data_paths(torrent):
    directory = PurePosixPath(torrent['downloadDir'])
    if '..' in directory.parts:
        raise ValueError('Unsafe download directory')
    for prefix in ['/data/meta/downloads', '/downloads']:
        if directory.is_relative_to(prefix):
            directory = DOWNLOADS / directory.relative_to(prefix)
            break
    else:
        raise ValueError('Download directory outside managed downloads')
    result = []
    for file in torrent['files']:
        relative = PurePosixPath(file['name'])
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('Unsafe torrent file path')
        path = Path(directory / relative)
        if not path.resolve().is_relative_to(DOWNLOADS.resolve()):
            raise ValueError('Torrent file escapes download storage')
        result.append(path)
    return result


class Transmission:
    def __init__(self):
        obj = json.loads(subprocess.check_output(['docker', 'inspect', 'transmission'], timeout=30))[0]
        env = dict(item.split('=', 1) for item in obj['Config']['Env'] if '=' in item)
        self.auth = base64.b64encode((env['USER'] + ':' + env['PASS']).encode()).decode()
        self.session = ''
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def rpc(self, method, arguments):
        for _ in range(2):
            request = urllib.request.Request(
                'http://127.0.0.1:9091/transmission/rpc',
                data=json.dumps({'method': method, 'arguments': arguments}).encode(),
                headers={'Authorization': 'Basic ' + self.auth,
                         'X-Transmission-Session-Id': self.session})
            try:
                with self.opener.open(request, timeout=120) as response:
                    result = json.load(response)
                if result.get('result') != 'success':
                    raise RuntimeError('Transmission RPC failed')
                return result['arguments']
            except urllib.error.HTTPError as error:
                if error.code != 409:
                    raise RuntimeError('Transmission HTTP error ' + str(error.code)) from None
                self.session = error.headers['X-Transmission-Session-Id']
        raise RuntimeError('Transmission session negotiation failed')

    def torrents(self):
        return self.rpc('torrent-get', {'fields': FIELDS})['torrents']


def receipt(torrent, reason, action):
    # Never log tracker URLs: they contain private passkeys.
    return {'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'hash': torrent['hashString'], 'name': torrent['name'],
            'labels': torrent['labels'], 'bytes': torrent['totalSize'],
            'seconds_seeding': torrent.get('secondsSeeding'), 'reason': reason, 'action': action}


def cleanup(client, apply=False, audit=None):
    counts = Counter()
    initial = client.torrents()
    for candidate in initial:
        eligible, reason = decision(candidate)
        if not eligible:
            counts[reason] += 1
            continue
        paths = data_paths(candidate)
        if not apply:
            print(json.dumps(receipt(candidate, reason, 'would-remove')), flush=True)
            counts['would-remove'] += 1
            continue
        # Re-read the whole inventory before each mutation: labels, completion,
        # tracker identity and files may change while Sonarr/Radarr are active.
        current = client.torrents()
        torrent = next((t for t in current if t['hashString'] == candidate['hashString']), None)
        if torrent is None:
            counts['already-removed'] += 1
            continue
        eligible, reason = decision(torrent)
        if not eligible or data_paths(torrent) != paths:
            counts['changed-since-plan'] += 1
            continue
        # Transmission deletes by torrent root; don't touch overlapping payloads.
        roots = data_paths({**torrent, 'files': [
            {'name': PurePosixPath(f['name']).parts[0]} for f in torrent['files']]})
        roots = {p.resolve() for p in roots}
        other_paths = set()
        for other in current:
            if other['hashString'] != torrent['hashString']:
                other_paths.update(p.resolve() for p in data_paths(other))
        if any(p == root or p.is_relative_to(root) for p in other_paths for root in roots):
            counts['shared-files'] += 1
            continue
        record = receipt(torrent, reason, 'remove-requested')
        audit(record)
        client.rpc('torrent-remove', {'ids': [torrent['hashString']], 'delete-local-data': True})
        for attempt in range(30):
            remaining = client.rpc('torrent-get', {'ids': [torrent['hashString']], 'fields': ['hashString']})['torrents']
            if not remaining and not any(os.path.lexists(p) for p in paths):
                break
            time.sleep(1)
        else:
            raise RuntimeError('Removal verification failed for ' + torrent['hashString'])
        record['action'] = 'removed'
        audit(record)
        print(json.dumps(record), flush=True)
        counts['removed'] += 1
    print(json.dumps({'apply': apply, 'scanned': len(initial), 'counts': counts}), flush=True)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true', help='Remove eligible torrents AND their download data')
    group.add_argument('--dry-run', action='store_true', help='Report only (the default)')
    args = parser.parse_args()
    if socket.gethostname().split('.')[0] != 'si':
        raise RuntimeError('This cleanup is only permitted on si')
    os.umask(0o077)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        def audit(record):
            with (STATE / 'removals.jsonl').open('a') as stream:
                stream.write(json.dumps(record) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
        cleanup(Transmission(), args.apply, audit)


if __name__ == '__main__':
    main()
