"""Policy compatibility and source routing; no installed commands or private data."""
import ast
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
NATIVE=ROOT/'system/native/si/files'

class ProtectionRouting(unittest.TestCase):
    def test_application_selection_and_recovery_allowlist_match_frozen_contract(self):
        source=ROOT/'system/tests/legacy/protection/backup.py'
        ns={}
        for node in ast.parse(source.read_text()).body:
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'app_excludes','plex','sources'}:
                exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
        policy=json.loads((NATIVE/'si-app-backup/policy.json').read_text())
        self.assertEqual(policy['sources'],json.loads(json.dumps(ns['sources']).replace('/home/m/.local/share/dotjik', '/home/m/code/dotjik')) + [['/var/lib/tasktjik', []], ['/var/lib/notjik', []], ['/var/lib/notjik-system-client', []]])
        for node in ast.parse((ROOT/'system/tests/legacy/protection/restore.py').read_text()).body:
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'DEFAULTS','EXTRA'}:
                key='restore_defaults' if node.targets[0].id=='DEFAULTS' else 'restore_extra'
                self.assertEqual(policy[key],ast.literal_eval(node.value) + (['/var/lib/tasktjik'] if key == 'restore_extra' else []))
        self.assertEqual(policy['restic']['keep_daily'],7)
        self.assertEqual(policy['restic']['keep_weekly'],4)
        self.assertEqual(policy['mariadb']['receipt'],'/var/lib/si-provision/mariadb-restored.json')

    def test_all_protection_units_route_to_native_engines(self):
        for path in (NATIVE/'systemd/system').glob('si-*.service'):
            if not path.name.startswith(('si-app-backup','si-snapraid')):continue
            content=path.read_text()
            self.assertNotIn('python',content)
            if path.name!='si-app-backup-failure.service':self.assertIn('/usr/local/bin/synctjik ',content)
        home=ROOT/'native/home/files/.config/systemd/user'
        for name,cmd in [('drive-restic-backup.service','drive backup'),('si-app-backup-pull.service','app-pull copy'),('si-app-backup-health.service','app-pull health')]:
            self.assertIn('ExecStart=%h/.local/bin/synctjik '+cmd,(home/name).read_text())
        for name in ['drive-restic-backup','si-app-backup-pull']:
            content=(ROOT/'native/home/files/.local/bin'/name).read_text()
            self.assertIn('exec ',content);self.assertNotIn('python',content);self.assertLess(len(content.splitlines()),5)

    def test_manifest_retires_engines_and_owns_policy(self):
        entries={e['path']:e for e in json.loads((NATIVE.parent/'manifest.json').read_text())['entries']}
        for name in ['si-app-backup/backup.py','si-provision/restore.py','si-snapraid-maintenance/maintenance.py','si-snapraid-maintenance/notify.py']:
            self.assertEqual(entries['/etc/'+name]['kind'],'absent')
            self.assertFalse((NATIVE/name).exists())
        for name in ['si-app-backup/policy.json','si-snapraid-maintenance/config.json','si-snapraid-maintenance/notifications.json']:
            self.assertEqual(entries['/etc/'+name]['source'],'files/'+name)

    def test_drive_copy_and_snapraid_policy_keep_durability_contract(self):
        home=ROOT/'native/home/files/.config/synctjik'
        drive=json.loads((home/'drive.json').read_text())
        self.assertEqual(drive['export_formats'],'docx,xlsx,pptx,svg')
        self.assertEqual([(s['tag'],s['source'],s['name']) for s in drive['sources']], [('private-archives','type-drive:private/archives','archives'),('gsuite','type-drive:GSUITE','gsuite')])
        self.assertEqual([drive['restic']['keep_'+x] for x in ['daily','weekly','monthly']],[1,1,1])
        pull=json.loads((home/'app-pull.json').read_text())
        self.assertEqual([pull[x] for x in ['copy_attempts','retry_seconds','limit_download','copy_max_hours','health_max_hours','weekly_offset_seconds','weekly_weekday','weekly_hour']],[3,10,2048,36,24,28800,0,6])
        snap=json.loads((NATIVE/'si-snapraid-maintenance/config.json').read_text())
        self.assertEqual(snap['max_removed'],200)
        self.assertEqual(snap['lock'],'/run/lock/si-snapraid-maintenance.lock')
        self.assertEqual(snap['backup_lock'],'/run/lock/si-app-backup.lock')
        for mode in ['sync','scrub']:
            self.assertIn('ExecStopPost=/usr/local/bin/synctjik snapraid resume',(NATIVE/'systemd/system'/('si-snapraid-'+mode+'.service')).read_text())

if __name__=='__main__':unittest.main()
