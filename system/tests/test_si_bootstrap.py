import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'etc/si-provision'))
import provision
import restore

class BootstrapTests(unittest.TestCase):
 def test_account_collision_causes_no_mutations(self):
  user=NS(pw_uid=999,pw_gid=1000,pw_dir='/home/m',pw_name='m')
  with patch.object(provision.pwd,'getpwnam',return_value=user),patch.object(provision.pwd,'getpwuid',return_value=user),patch.object(provision.grp,'getgrnam',side_effect=KeyError),patch.object(provision.grp,'getgrgid',side_effect=KeyError),patch.object(provision,'run') as run:
   with self.assertRaises(RuntimeError):provision.accounts(True)
   run.assert_not_called()
 def test_existing_accounts_not_recreated(self):
  with patch.object(provision,'account_plan',return_value=iter([('m',1000,1000,'/home/m','/bin/fish',True,True)])),patch.object(provision,'get',return_value=None),patch.object(provision,'run') as run:
   provision.accounts(True)
   self.assertEqual([x.args[0] for x in run.call_args_list],['usermod'])
 def test_installed_mergerfs_never_upgraded(self):
  with patch.object(provision.subprocess,'run',return_value=NS(returncode=0,stdout='mergerfs-old')),patch.object(provision.urllib.request,'urlretrieve') as download:
   provision.mergerfs(True);download.assert_not_called()
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
  with patch.object(restore,'CONFIG',ROOT/'etc/si-snapraid-maintenance/config.json'),patch.object(restore,'check_mounts'),patch.object(restore,'quiet_services'),patch.object(restore,'root_for',return_value=ROOT),patch.object(restore,'validate'),patch.object(restore,'run') as run:
   with self.assertRaises(RuntimeError):restore.install(NS(stage=ROOT,include=['/etc']))
   run.assert_not_called()
 def test_bad_database_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'test.db').write_text('not a database')
   (root/'backup-manifest.json').write_text(json.dumps({'sqlite':[{'path':'/test.db'}],'mariadbDump':'database-dumps/mariadb.sql'}))
   with self.assertRaises(Exception):restore.validate(root)
 def test_runtime_apply_cannot_run_restore(self):
  scripts=ROOT/'etc/.chezmoitemplates/tjikup'
  for p in scripts.iterdir():self.assertNotIn('restore.py',p.read_text())
  for name in ['run_30-system-update.fish.tmpl','run_40-enable-docker.fish.tmpl','run_90-build-nginx-dav-ext.fish.tmpl']:
   s=(scripts/name).read_text();self.assertNotIn('Server lifecycle step skipped',s)
if __name__=='__main__':unittest.main()
