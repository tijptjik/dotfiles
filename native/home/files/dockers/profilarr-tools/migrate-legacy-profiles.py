#!/usr/bin/env python3
"""Migrate si's legacy profile references through supported APIs.

Dry-run by default. Explicit --apply on si is required. Approved Seerr request
history is the only direct DB edit: its API refuses approved requests, so that
small transaction runs with Seerr stopped and a SQLite backup in hand.
No searches, notifications, file moves or monitoring changes are requested.
"""
import argparse
import collections
import datetime
import json
import os
import pathlib
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

APPDATA = pathlib.Path('/mnt/storage/meta/appData')
MAPPING = pathlib.Path(__file__).resolve().parent.parent / 'profilarr-database/legacy-migration.json'
PORTS = {'radarr': 7878, 'sonarr': 8989}


def call(port, key, route, body=None, method=None):
    request = urllib.request.Request(
        f'http://127.0.0.1:{port}/api/' + ('v1/' if port == 5055 else 'v3/') + route,
        headers={'X-Api-Key': key, 'Content-Type': 'application/json'},
        data=None if body is None else json.dumps(body).encode(), method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
            return json.loads(data) if data else None
    except urllib.error.HTTPError as error:
        # Provider/configuration payloads may contain keys. Never echo bodies.
        raise RuntimeError(f'{route}: HTTP {error.code}; response body suppressed') from None


def arr(app, route, body=None, method=None):
    key = ET.parse(APPDATA / app / 'config.xml').findtext('ApiKey')
    return call(PORTS[app], key, route, body, method)


def save_private(path, value):
    with open(path, 'w', opener=lambda p, flags: os.open(p, flags, 0o600)) as handle:
        json.dump(value, handle)


def invariant(record):
    fields = ('path', 'rootFolderPath', 'monitored', 'minimumAvailability', 'seriesType', 'seasonFolder')
    result = {key: record.get(key) for key in fields if key in record}
    result['tags'] = sorted(record.get('tags', []))
    if 'seasons' in record:
        result['seasons'] = {s['seasonNumber']: s['monitored'] for s in record['seasons']}
    return result


def inventory(spec):
    state = {}
    for app in PORTS:
        profiles = arr(app, 'qualityprofile')
        by_name = {p['name']: p for p in profiles}
        by_id = {p['id']: p for p in profiles}
        mapping = {}
        legacy = []
        for rule in spec['mappings'][app]:
            if rule['targetName'] not in by_name:
                raise RuntimeError(f'{app}: missing target {rule["targetName"]}')
            old = by_name.get(rule['legacyName'])
            old_id = old['id'] if old else rule['legacyId']
            if not old and old_id in by_id:
                raise RuntimeError(f'{app}: legacy ID {old_id} belongs to another profile')
            mapping[old_id] = by_name[rule['targetName']]['id']
            if old:
                legacy.append(old)
        allowed_names = {a['name'] for a in spec['targets']}
        unknown = [p['name'] for p in profiles if p['name'] not in allowed_names and p not in legacy]
        if unknown:
            raise RuntimeError(f'{app}: unmapped profiles {unknown}')
        entity = 'movie' if app == 'radarr' else 'series'
        media = arr(app, entity)
        lists = arr(app, 'importlist')
        collections_ = arr(app, 'collection') if app == 'radarr' else []
        rules = arr(app, 'autotagging')
        if rules:
            raise RuntimeError(f'{app}: inspect autotagging rules before proceeding')
        state[app] = dict(profiles=profiles, mapping=mapping, legacy=legacy, media=media,
                          entity=entity, lists=lists, collections=collections_)
        counts = collections.Counter(x['qualityProfileId'] for x in media)
        for rule in spec['mappings'][app]:
            old = by_name.get(rule['legacyName'])
            print(app, rule['legacyName'], '->', rule['targetName'],
                  counts[old['id']] if old else 0, flush=True)
    return state


def backup(state, seerr_settings, backup_dir):
    for app, data in state.items():
        save_private(backup_dir / (app + '.json'), data)
        command = arr(app, 'command', {'name': 'Backup'})
        for _ in range(150):
            status = arr(app, 'command/' + str(command['id']))
            value = status.get('status', status.get('state'))
            if value == 'completed':
                print(app, 'native backup completed', flush=True)
                break
            if value in ('failed', 'aborted', 'cancelled'):
                raise RuntimeError(f'{app}: native backup failed')
            time.sleep(2)
        else:
            raise RuntimeError(f'{app}: native backup did not finish')
    save_private(backup_dir / 'seerr-settings.json', seerr_settings)


def migrate_arr_references(app, data):
    mapping = data['mapping']
    for entry in data['lists']:
        if entry.get('qualityProfileId') in mapping:
            entry['qualityProfileId'] = mapping[entry['qualityProfileId']]
            arr(app, 'importlist/' + str(entry['id']), entry, 'PUT')
    print(app, len(data['lists']), 'import lists checked/migrated', flush=True)
    for index, entry in enumerate(data['collections'], 1):
        if entry['qualityProfileId'] in mapping:
            entry['qualityProfileId'] = mapping[entry['qualityProfileId']]
            # The per-ID endpoint does not queue a collection refresh/search.
            arr(app, 'collection/' + str(entry['id']), entry, 'PUT')
        if index % 50 == 0:
            print(app, 'collections', index, '/', len(data['collections']), flush=True)
    grouped = collections.defaultdict(list)
    for record in data['media']:
        if record['qualityProfileId'] in mapping:
            grouped[record['qualityProfileId']].append(record['id'])
    ids_key = 'movieIds' if app == 'radarr' else 'seriesIds'
    for old_id, ids in grouped.items():
        for offset in range(0, len(ids), 250):
            batch = ids[offset:offset + 250]
            arr(app, data['entity'] + '/editor',
                {ids_key: batch, 'qualityProfileId': mapping[old_id]}, 'PUT')
        print(app, 'migrated', len(ids), 'items from profile', old_id,
              'to', mapping[old_id], flush=True)


def migrate_seerr_settings(state, settings):
    key = settings['main']['apiKey']
    for app in PORTS:
        for entry in call(5055, key, 'settings/' + app):
            changed = False
            for prefix in ('activeProfile', 'activeAnimeProfile'):
                field = prefix + 'Id'
                if entry.get(field) in state[app]['mapping']:
                    target = state[app]['mapping'][entry[field]]
                    entry[field] = target
                    entry[prefix + 'Name'] = next(p['name'] for p in state[app]['profiles'] if p['id'] == target)
                    changed = True
            if changed:
                call(5055, key, 'settings/' + app + '/' + str(entry['id']),
                     {k: v for k, v in entry.items() if k != 'id'}, 'PUT')
        print('Seerr', app, 'defaults migrated', flush=True)


def migrate_request_history(state, settings, backup_dir):
    db_path = APPDATA / 'seerr/db/db.sqlite3'
    # API editing of approved requests is forbidden and ORM save would send
    # notifications. A stopped-writer transaction changes only external IDs.
    result = subprocess.run(['docker', 'stop', '--time', '30', 'seerr'], capture_output=True)
    if result.returncode:
        raise RuntimeError('Could not stop Seerr for the request-reference transaction')
    connection = None
    try:
        connection = sqlite3.connect(db_path, timeout=30, isolation_level=None)
        connection.execute('PRAGMA foreign_keys=ON')
        snapshot_path = backup_dir / 'seerr.sqlite3'
        with sqlite3.connect(snapshot_path) as destination:
            connection.backup(destination)
        snapshot_path.chmod(0o600)
        rows_before = connection.execute('SELECT * FROM media_request ORDER BY id').fetchall()
        columns = [c[1] for c in connection.execute('PRAGMA table_info(media_request)')]
        if connection.execute('SELECT COUNT(*) FROM override_rule').fetchone()[0]:
            raise RuntimeError('Unexpected Seerr override rules; inspect before migration')
        connection.execute('BEGIN IMMEDIATE')
        count = 0
        for app, kind in [('radarr', 'movie'), ('sonarr', 'tv')]:
            server_ids = [s['id'] for s in settings[app]]
            placeholders = ','.join('?' for _ in server_ids)
            for old, new in state[app]['mapping'].items():
                cursor = connection.execute(
                    f'UPDATE media_request SET profileId=? WHERE profileId=? AND type=? AND serverId IN ({placeholders})',
                    [new, old, kind, *server_ids],
                )
                count += cursor.rowcount
        rows_after = connection.execute('SELECT * FROM media_request ORDER BY id').fetchall()
        assert len(rows_before) == len(rows_after), 'Request history row count changed'
        position = columns.index('profileId')
        for old, new in zip(rows_before, rows_after):
            assert all(old[i] == new[i] for i in range(len(columns)) if i != position), 'Non-profile request field changed'
        assert not connection.execute('PRAGMA foreign_key_check').fetchall(), 'Seerr foreign key check failed'
        connection.execute('COMMIT')
        print('Seerr historical request profile IDs migrated:', count, flush=True)
    finally:
        if connection is not None:
            if connection.in_transaction:
                connection.execute('ROLLBACK')
            connection.close()
        result = subprocess.run(['docker', 'start', 'seerr'], capture_output=True)
        if result.returncode:
            raise RuntimeError('Seerr restart failed')
    for _ in range(60):
        try:
            call(5055, settings['main']['apiKey'], 'status')
            return
        except (RuntimeError, OSError):
            time.sleep(1)
    raise RuntimeError('Seerr did not become ready')


def verify_arr(app, data):
    current = arr(app, data['entity'])
    by_id = {x['id']: x for x in current}
    allowed = {p['id'] for p in data['profiles'] if p not in data['legacy']}
    for before in data['media']:
        after = by_id[before['id']]
        expected = data['mapping'].get(before['qualityProfileId'], before['qualityProfileId'])
        assert after['qualityProfileId'] == expected, (app, before['id'], 'profile mismatch')
        assert invariant(before) == invariant(after), (app, before['id'], 'path/monitoring/tags changed')
    assert all(x['qualityProfileId'] in allowed for x in current), app + ': legacy media assignment remains'
    for route in ('importlist', 'collection') if app == 'radarr' else ('importlist',):
        values = arr(app, route)
        assert all(x.get('qualityProfileId') in allowed for x in values), app + ': legacy ' + route + ' reference'
        if route == 'collection':
            after_collections = {x['id']: x for x in values}
            for before in data['collections']:
                assert invariant(before) == invariant(after_collections[before['id']]), 'Collection settings changed'
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--mapping', type=pathlib.Path, default=MAPPING)
    args = parser.parse_args()
    spec = json.loads(args.mapping.read_text())
    policy = json.loads((args.mapping.parent / 'policy.json').read_text())
    spec['targets'] = policy['tiers']
    if args.apply and (socket.gethostname().split('.')[0] != spec['host'] or os.geteuid() != 0):
        parser.error('--apply must run as root on si')
    state = inventory(spec)
    settings_path = APPDATA / 'seerr/settings.json'
    if not settings_path.exists():
        settings_path = next((APPDATA / 'seerr').rglob('settings.json'))
    settings = json.loads(settings_path.read_text())
    if not args.apply:
        print('Dry run only; use --apply on si after reviewing the mapping.')
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_dir = APPDATA / 'profilarr/backups' / ('profile-migration-' + stamp)
    backup_dir.mkdir(mode=0o700, parents=True)
    save_private(backup_dir / 'mapping.json', spec)
    backup(state, settings, backup_dir)
    migrate_seerr_settings(state, settings)
    for app, data in state.items():
        migrate_arr_references(app, data)
        verify_arr(app, data)
    migrate_request_history(state, settings, backup_dir)
    for app, data in state.items():
        allowed = {p['id'] for p in data['profiles'] if p not in data['legacy']}
        for entry in call(5055, settings['main']['apiKey'], 'settings/' + app):
            for field in ('activeProfileId', 'activeAnimeProfileId'):
                if entry.get(field) is not None:
                    assert entry[field] in allowed, 'Seerr still references a legacy profile'
    for app, data in state.items():
        verify_arr(app, data)
        for old in data['legacy']:
            arr(app, 'qualityprofile/' + str(old['id']), method='DELETE')
        remaining = arr(app, 'qualityprofile')
        assert {x['name'] for x in remaining} == {x['name'] for x in policy['tiers']}
        counts = collections.Counter(x['qualityProfileId'] for x in arr(app, data['entity']))
        print(app, 'FINAL', {p['name']: counts[p['id']] for p in remaining}, flush=True)
        call(5055, settings['main']['apiKey'], 'settings/cache/' + app + '/flush', {}, 'POST')
        service = call(5055, settings['main']['apiKey'], 'service/' + app + '/' + str(settings[app][0]['id']))
        assert {p['name'] for p in service['profiles']} == {p['name'] for p in policy['tiers']}
    print('PASS: only the 12 new profiles remain; paths, monitoring and tags preserved.', flush=True)
    print('Rollback snapshots:', backup_dir, flush=True)


if __name__ == '__main__':
    main()
