import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).resolve().parents[1] / 'scripts/cleanup-launcher-entries.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)

class CleanupTests(unittest.TestCase):
    def test_archives_orphan_but_preserves_registered_pwa(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);apps=home/'.local/share/applications';apps.mkdir(parents=True)
            old='FFPWA-01KC3V7SZSJ8PMK49J7QBTP2FK.desktop';new=cleanup.REPLACEMENTS[old]
            (apps/old).write_text('old');(apps/new).write_text('new')
            registry=home/'.local/share/firefoxpwa/config.json';registry.parent.mkdir()
            registry.write_text(json.dumps({'sites':{old[6:-8]:{},new[6:-8]:{}}}))
            with patch.object(cleanup.shutil,'which',return_value=None):
                self.assertEqual(cleanup.cleanup(home,True)['changes'],[])
                registry.write_text(json.dumps({'sites':{new[6:-8]:{}}}))
                self.assertEqual(len(cleanup.cleanup(home)['changes']),1)
                self.assertTrue((apps/old).exists())
                result=cleanup.cleanup(home,True)
            self.assertFalse((apps/old).exists())
            self.assertEqual((Path(result['archive'])/'.local/share/applications'/old).read_text(),'old')
            self.assertEqual((apps/new).read_text(),'new')

    def test_missing_canonical_is_not_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);apps=home/'.local/share/applications';apps.mkdir(parents=True)
            (apps/'dev.zed.desktop').write_text('keep')
            with patch.object(cleanup.shutil,'which',return_value=None):
                self.assertEqual(cleanup.cleanup(home,True)['changes'],[])
            self.assertTrue((apps/'dev.zed.desktop').exists())
