import contextlib
import copy
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cleanup', ROOT / 'etc/si-transmission-cleanup/cleanup.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


def torrent(**changes):
    value = {'hashString': 'a' * 40, 'name': 'Example', 'labels': ['sonarr'],
             'metadataPercentComplete': 1, 'percentDone': 1, 'leftUntilDone': 0,
             'totalSize': 100, 'files': [{'name': 'Example/video.mkv', 'length': 100, 'bytesCompleted': 100}],
             'downloadDir': '/downloads/sonarr', 'secondsSeeding': 0,
             'isPrivate': False, 'trackers': [{'announce': 'udp://tracker.example.org/announce'}]}
    value.update(changes)
    return value


class PolicyTests(unittest.TestCase):
    def test_only_exact_managed_labels(self):
        for label in cleanup.LABELS:
            self.assertTrue(cleanup.decision(torrent(labels=[label]))[0])
        for labels in [[], ['book'], ['lazy'], ['my-sonarr'], ['SONARR']]:
            self.assertFalse(cleanup.decision(torrent(labels=labels))[0])

    def test_fully_downloaded_not_selected_files_only(self):
        for change in [{'percentDone': .99}, {'metadataPercentComplete': .5},
                       {'leftUntilDone': 1}, {'totalSize': 0}, {'files': []},
                       {'files': [{'name': 'a', 'length': 100, 'bytesCompleted': 0}]}]:
            self.assertFalse(cleanup.decision(torrent(**change))[0])
        for key in ['percentDone', 'metadataPercentComplete', 'leftUntilDone', 'totalSize', 'files']:
            t = torrent(); del t[key]
            self.assertFalse(cleanup.decision(t)[0])

    def test_ipt_aliases_and_strict_time_boundary(self):
        for host in cleanup.IPT_HOSTS | {'iptorrents.me', 'tracker.iptorrents.com'}:
            t = torrent(isPrivate=True, trackers=[{'announce': 'https://' + host + '/private-passkey/announce'}])
            for seconds in [0, -1, None, cleanup.MIN_SEED_SECONDS]:
                t['secondsSeeding'] = seconds
                self.assertFalse(cleanup.decision(t)[0])
            t['secondsSeeding'] = cleanup.MIN_SEED_SECONDS + 1
            self.assertEqual(cleanup.decision(t), (True, 'ipt'))
            t['trackers'].append({'announce': 'udp://public.example.org/announce'})
            t['secondsSeeding'] = 1
            self.assertFalse(cleanup.decision(t)[0])

    def test_unknown_private_or_tracker_metadata_fails_closed(self):
        for change in [{'isPrivate': True}, {'isPrivate': None}, {'trackers': []},
                       {'trackers': [{}]}, {'trackers': [{'announce': 'not-a-url'}]},
                       {'isPrivate': True, 'trackers': [{'announce': 'https://iptorrents.me.evil.test/a'}]}]:
            self.assertFalse(cleanup.decision(torrent(**change))[0])

    def test_paths_cannot_escape_downloads(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(cleanup, 'DOWNLOADS', Path(directory)):
            self.assertEqual(cleanup.data_paths(torrent())[0], Path(directory) / 'sonarr/Example/video.mkv')
            for location in ['/data/library', '/downloads-other', '/downloads/../library']:
                with self.assertRaises(ValueError): cleanup.data_paths(torrent(downloadDir=location))
            for name in ['../library/video', '/etc/passwd', '']:
                with self.assertRaises(ValueError): cleanup.data_paths(torrent(files=[{'name': name}]))
            (Path(directory) / 'escape').symlink_to('/etc')
            with self.assertRaises(ValueError):
                cleanup.data_paths(torrent(downloadDir='/downloads', files=[{'name': 'escape/passwd'}]))

    def test_logs_have_no_passkey(self):
        t = torrent(trackers=[{'announce': 'https://ssl.empirehost.me/SECRET'}])
        self.assertNotIn('SECRET', str(cleanup.receipt(t, 'ipt', 'removed')))


class FakeClient:
    def __init__(self, snapshots):
        self.snapshots = snapshots
        self.calls = []
    def torrents(self):
        return copy.deepcopy(self.snapshots.pop(0))
    def rpc(self, method, args):
        self.calls.append((method, args))
        return {'torrents': []}


class RemovalTests(unittest.TestCase):
    def run_cleanup(self, client, apply):
        with tempfile.TemporaryDirectory() as directory, patch.object(cleanup, 'DOWNLOADS', Path(directory)), contextlib.redirect_stdout(io.StringIO()):
            records = []
            counts = cleanup.cleanup(client, apply, lambda r: records.append(copy.deepcopy(r)))
            return counts, records

    def test_dry_run_never_mutates(self):
        client = FakeClient([[torrent()]])
        counts, records = self.run_cleanup(client, False)
        self.assertEqual(counts['would-remove'], 1)
        self.assertEqual(client.calls, [])
        self.assertEqual(records, [])

    def test_recheck_prevents_removal_after_label_change(self):
        client = FakeClient([[torrent()], [torrent(labels=['book'])]])
        counts, records = self.run_cleanup(client, True)
        self.assertEqual(counts['changed-since-plan'], 1)
        self.assertEqual(client.calls, [])

    def test_overlapping_root_is_retained(self):
        other = torrent(hashString='b' * 40, labels=['book'], files=[{'name': 'Example/other.mkv', 'length': 100, 'bytesCompleted': 100}])
        client = FakeClient([[torrent()], [torrent(), other]])
        counts, records = self.run_cleanup(client, True)
        self.assertEqual(counts['shared-files'], 1)
        self.assertEqual(client.calls, [])

    def test_remove_uses_hash_and_deletes_data_then_verifies(self):
        client = FakeClient([[torrent()], [torrent()]])
        counts, records = self.run_cleanup(client, True)
        self.assertEqual(client.calls[0], ('torrent-remove', {'ids': ['a' * 40], 'delete-local-data': True}))
        self.assertEqual(client.calls[1][0], 'torrent-get')
        self.assertEqual(counts['removed'], 1)
        self.assertEqual([r['action'] for r in records], ['remove-requested', 'removed'])

    def test_rpc_failure_is_not_reported_as_success(self):
        client = FakeClient([[torrent()], [torrent()]])
        with patch.object(client, 'rpc', side_effect=TimeoutError):
            with self.assertRaises(TimeoutError): self.run_cleanup(client, True)


if __name__ == '__main__':
    unittest.main()
