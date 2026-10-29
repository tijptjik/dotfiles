import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tests/legacy/protection/notify.py'
if not SOURCE.exists():
    SOURCE = Path(__file__).with_name('notify.py')
spec = importlib.util.spec_from_file_location('snapraid_notifications', SOURCE)
notify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify)


class Notifications(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ['STATE', 'RECEIPTS']:
            p = self.root / name
            p.mkdir()
            patcher = patch.object(notify, name, p)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.unit = 'si-snapraid-sync.service'
        self.now = dt.datetime(2026, 10, 22, tzinfo=dt.timezone.utc)
        self.send = patch.object(notify, 'send', return_value=42).start()
        self.addCleanup(patch.stopall)

    def test_failure_once_reminder_after_day_and_recovery_once(self):
        notify.incident(self.unit, '201 removals exceed limit 200', self.now)
        notify.incident(self.unit, '201 removals exceed limit 200', self.now + dt.timedelta(hours=1))
        self.assertEqual(self.send.call_count, 1)
        notify.incident(self.unit, '201 removals exceed limit 200', self.now + dt.timedelta(days=1))
        self.assertEqual(self.send.call_count, 2)
        notify.recover(self.unit)
        notify.recover(self.unit)
        self.assertEqual(self.send.call_count, 3)
        self.assertIn('recovered', self.send.call_args.args[0].lower())

    def test_changed_incident_delivery_failure_is_retried(self):
        notify.incident(self.unit, 'old issue', self.now)
        self.send.side_effect = RuntimeError('offline')
        with self.assertRaises(RuntimeError):
            notify.incident(self.unit, 'new issue', self.now + dt.timedelta(hours=1))
        self.send.side_effect = None
        notify.incident(self.unit, 'new issue', self.now + dt.timedelta(hours=1))
        self.assertEqual(self.send.call_count, 3)

    def test_healthy_start_does_not_send_success_spam(self):
        notify.recover(self.unit)
        self.send.assert_not_called()

    def test_fresh_receipts_and_missed_runs_without_parity_commands(self):
        for mode in ['sync', 'scrub']:
            (notify.RECEIPTS / f'last-{mode}-success.json').write_text(json.dumps({'completed_at': self.now.isoformat()}))
        with patch.object(notify, 'utcnow', return_value=self.now), patch.object(notify, 'unit_status', return_value={'ActiveState': 'inactive', 'Result': 'success'}):
            notify.health()
            self.send.assert_not_called()
            (notify.RECEIPTS / 'last-sync-success.json').unlink()
            notify.health()
            self.send.assert_called_once()
            self.assertIn('No verified successful sync', self.send.call_args.args[0])

    def test_running_job_is_not_a_missed_run_but_hung_job_alerts(self):
        statuses = [{'ActiveState': 'activating', 'ExecMainStartTimestampMonotonic': str(1000 * 1000000)}, {'ActiveState': 'activating', 'ExecMainStartTimestampMonotonic': str(1000 * 1000000)}]
        with patch.object(notify, 'unit_status', side_effect=statuses), patch.object(notify.time, 'monotonic', return_value=1100):
            notify.health()
        self.send.assert_not_called()
        statuses = [{'ActiveState': 'activating', 'ExecMainStartTimestampMonotonic': '1000000'}, {'ActiveState': 'activating', 'ExecMainStartTimestampMonotonic': '1000000'}]
        with patch.object(notify, 'unit_status', side_effect=statuses), patch.object(notify.time, 'monotonic', return_value=140000):
            notify.health()
        self.send.assert_called_once()
        self.assertIn('running longer', self.send.call_args.args[0])

    def test_corrupt_success_receipt_alerts(self):
        (notify.RECEIPTS / 'last-sync-success.json').write_text('broken')
        (notify.RECEIPTS / 'last-scrub-success.json').write_text(json.dumps({'completed_at': self.now.isoformat()}))
        with patch.object(notify, 'utcnow', return_value=self.now), patch.object(notify, 'unit_status', return_value={'ActiveState': 'inactive'}):
            notify.health()
        self.send.assert_called_once()


if __name__ == '__main__':
    unittest.main()
