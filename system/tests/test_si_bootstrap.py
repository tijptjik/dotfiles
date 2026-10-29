import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/legacy/protection'))
spec=importlib.util.spec_from_file_location('restore',ROOT/'tests/legacy/protection/restore.py')
restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)

class BootstrapTests(unittest.TestCase):
 def test_restore_refuses_existing_data_and_symlinks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'target';p.mkdir();restore.require_empty(p)
   (p/'database').write_text('important')
   with self.assertRaises(RuntimeError):restore.require_empty(p)
   link=Path(d)/'link';link.symlink_to(p)
   with self.assertRaises(RuntimeError):restore.require_empty(link)
   self.assertEqual((p/'database').read_text(),'important')
 def test_restore_never_accepts_latest(self):
  with self.assertRaises(RuntimeError):restore.stage_restore(NS(snapshot='latest'))
 def test_restore_live_writers_blocked(self):
  with patch.object(restore.subprocess,'run',return_value=NS(returncode=0)),patch.object(restore.subprocess,'check_output',return_value='sonarr\nmariadb\n'):
   with self.assertRaises(RuntimeError):restore.quiet_services(True)
 def test_restore_no_copy_before_all_destinations_checked(self):
  with patch.object(restore,'CONFIG',ROOT/'native/si/files/si-snapraid-maintenance/config.json'),patch.object(restore,'check_mounts'),patch.object(restore,'quiet_services'),patch.object(restore,'root_for',return_value=ROOT),patch.object(restore,'validate'),patch.object(restore,'run') as run:
   with self.assertRaises(RuntimeError):restore.install(NS(stage=ROOT,include=['/etc']))
   run.assert_not_called()
 def test_bad_database_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'test.db').write_text('not a database')
   (root/'backup-manifest.json').write_text(json.dumps({'sqlite':[{'path':'/test.db'}],'mariadbDump':'database-dumps/mariadb.sql'}))
   with self.assertRaises(Exception):restore.validate(root)
 def test_runtime_apply_cannot_run_restore(self):
  scripts=ROOT/'../native/tasks/system'
  for p in scripts.iterdir():self.assertNotIn('restore.py',p.read_text())
  for name in ['run_30-system-update.fish.j2','run_40-enable-docker.fish.j2','run_90-build-nginx-dav-ext.fish.j2']:
   s=(scripts/name).read_text();self.assertNotIn('Server lifecycle step skipped',s)
if __name__=='__main__':unittest.main()
