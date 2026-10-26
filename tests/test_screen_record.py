import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('screen_record', str(ROOT/'home/dot_local/bin/executable_screen-record'))
spec = importlib.util.spec_from_loader(loader.name, loader)
recorder = importlib.util.module_from_spec(spec)
loader.exec_module(recorder)


class ScreenRecordTests(unittest.TestCase):
    def test_geometry_and_video_path_are_passed_as_individual_arguments(self):
        command = recorder.recorder_command('100x200+-1920+0', Path('/tmp/My videos/test.mp4'))
        self.assertIn('100x200+-1920+0', command)
        self.assertEqual(command[-1], '/tmp/My videos/test.mp4')
        self.assertIn('default_output', command)
        for region in ('', '0x100+0+0', '10x10+0+0;rm', '10x10 0,0'):
            with self.assertRaises(ValueError): recorder.recorder_command(region, 'test.mp4')

    def test_toggle_stops_active_or_pending_service_and_starts_inactive(self):
        for state in ('active', 'activating', 'deactivating', 'inactive', 'failed'):
            with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': tmp}), \
                 patch.object(recorder.subprocess, 'check_output', return_value=state), \
                 patch.object(recorder.subprocess, 'run') as run:
                recorder.toggle()
                expected = 'start' if state in ('inactive', 'failed') else 'stop'
                self.assertEqual(run.call_args.args[0], ['systemctl', '--user', expected, recorder.UNIT])

    def test_cancelled_selection_never_starts_recording(self):
        child = Mock(returncode=1)
        child.communicate.return_value = ('', None)
        with patch.object(recorder.signal, 'signal'), patch.object(recorder.subprocess, 'Popen', return_value=child) as popen:
            recorder.record()
        self.assertEqual(popen.call_count, 1)

    def test_cancelled_countdown_never_starts_recording(self):
        selection = Mock(returncode=0)
        selection.communicate.return_value = ('100x100+0+0', None)
        countdown = Mock()
        countdown.wait.return_value = 0
        stopped = Mock()
        stopped.is_set.side_effect = [False, False, False, True]
        with patch.object(recorder.signal, 'signal'), patch.object(recorder.threading, 'Event', return_value=stopped), \
             patch.object(recorder, 'notify') as notify, \
             patch.object(recorder.subprocess, 'Popen', side_effect=[selection, countdown]) as popen:
            recorder.record()
        self.assertEqual(popen.call_count, 2)
        self.assertIn('countdown', popen.call_args.args[0])
        notify.assert_not_called()

    def test_cancel_during_overlay_settle_does_not_start_capture(self):
        selection = Mock(returncode=0)
        selection.communicate.return_value = ('100x100+0+0', None)
        countdown = Mock()
        countdown.wait.return_value = 0
        stopped = Mock()
        stopped.is_set.return_value = False
        stopped.wait.return_value = True
        with patch.object(recorder.signal, 'signal'), patch.object(recorder.threading, 'Event', return_value=stopped), \
             patch.object(recorder.subprocess, 'Popen', side_effect=[selection, countdown]) as popen:
            recorder.record()
        stopped.wait.assert_called_once_with(0.5)
        self.assertEqual(popen.call_count, 2)

    def test_window_capture_uses_portal_with_fresh_picker(self):
        command = recorder.recorder_command(None, 'window.mp4', 'window')
        self.assertEqual(command[1:5], ['-w', 'portal', '-restore-portal-session', 'no'])
        self.assertNotIn('-region', command)

    def test_monitor_picker_restricts_selection_to_outputs(self):
        child = Mock(returncode=1)
        child.communicate.return_value = ('', None)
        with patch.object(recorder.signal, 'signal'), patch.object(recorder.subprocess, 'Popen', return_value=child) as popen:
            recorder.record('monitor')
        self.assertEqual(popen.call_args.args[0], ['slurp', '-o', '-r', '-f', '%wx%h+%x+%y'])
        self.assertEqual(popen.call_count, 1)

    def test_mode_is_saved_only_when_starting(self):
        for state in ('active', 'inactive'):
            with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_RUNTIME_DIR': tmp}), \
                 patch.object(recorder.subprocess, 'check_output', return_value=state), \
                 patch.object(recorder.subprocess, 'run'):
                mode_path = Path(tmp) / 'screen-record-mode'
                mode_path.write_text('region')
                recorder.toggle('window')
                self.assertEqual(mode_path.read_text(), 'window' if state == 'inactive' else 'region')
