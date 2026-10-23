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
        child = Mock(returncode=0)
        child.communicate.return_value = ('100x100+0+0', None)
        stopped = Mock()
        stopped.is_set.return_value = False
        stopped.wait.return_value = True
        with patch.object(recorder.signal, 'signal'), patch.object(recorder.threading, 'Event', return_value=stopped), \
             patch.object(recorder, 'notify'), patch.object(recorder.subprocess, 'Popen', return_value=child) as popen:
            recorder.record()
        self.assertEqual(popen.call_count, 1)
