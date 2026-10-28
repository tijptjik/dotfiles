import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

hook = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'home/dot_config/kitty/notifications.py'))

class KittyHookTests(unittest.TestCase):
    def test_local_binary_receives_only_display_metadata(self):
        data = {"state":"ALL SYSTEMS GO","duration":"1s","tone":"success","results":[]}
        command = SimpleNamespace(application_name="Tjikup", title="Remote", notification_types=["tjikup-status-v1:"+json.dumps({"data":data,"body":"done"})])
        with patch('subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertTrue(hook['main'](command))
        self.assertEqual(run.call_args.args[0], ['tjikup','notify','--stdin'])
        self.assertEqual(json.loads(run.call_args.kwargs['input']), {'title':'Remote','data':data,'body':'done'})

    def test_unknown_metadata_retains_normal_kitty_delivery(self):
        command = SimpleNamespace(application_name="Tjikup", title="Remote", notification_types=['tjikup-status-v1:{"command":["bad"]}'])
        with patch('subprocess.run') as run:
            self.assertFalse(hook['main'](command))
            run.assert_not_called()
