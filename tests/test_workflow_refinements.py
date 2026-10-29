"""Synthetic checks for review mode policy, package checks and safe timer migration."""
import importlib.util
import io
import contextlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class WorkflowRefinements(unittest.TestCase):
    def test_busy_legacy_backup_never_disables_a_timer_or_stops_a_job(self):
        migration=module('sync_migration','migrate-sync-units.py')
        with patch.object(migration,'legacy_units',return_value=migration.OLD_UNITS), patch.object(migration,'state',return_value={'LoadState':'loaded','ActiveState':'active'}), patch.object(migration.subprocess,'run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(migration.main(),1)
            run.assert_not_called()

    def test_idle_migration_only_disables_old_timers(self):
        migration=module('sync_migration','migrate-sync-units.py')
        with patch.object(migration,'legacy_units',return_value=migration.OLD_UNITS), patch.object(migration,'state',return_value={'LoadState':'loaded','ActiveState':'inactive'}), patch.object(migration.subprocess,'run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(migration.main(retire=True),0)
            self.assertEqual(run.call_count,len(migration.OLD_UNITS))
            for call in run.call_args_list:
                argv=call.args[0]
                self.assertEqual(argv[2:4],['disable','--now'])
                self.assertTrue(argv[-1].endswith('.timer'))

    def test_rpm_manifest_uses_one_fresh_query_per_call(self):
        package=module('package_task_refinement','package-task.py')
        policy={'sample':{'packages':'rpm'}}
        data={'packages':{'common':{'rpm':['a','b']},'client':{'rpm':['c']}}}
        def read(path,*args,**kwargs):
            return json.dumps(policy if path.name=='package-checks.json' else data)
        with patch.object(Path,'read_text',read), patch.object(package.subprocess,'run',side_effect=[
            subprocess.CompletedProcess([],0,'a\nb\nc\n',''),
            subprocess.CompletedProcess([],0,'a\nc\n','')]) as query:
            self.assertEqual(package.presence('sample','desktop'),[True,True,True])
            self.assertEqual(package.presence('sample','desktop'),[True,False,True])
            self.assertEqual(query.call_count,2)
            self.assertEqual(query.call_args.args[0][:2],['rpm','-qa'])

    def test_split_terminal_recipes_pass_selector_through_sudo(self):
        recipes=json.loads((ROOT/'system/tjikup/recipes.json').read_text())['recipes']
        for ident,tool in [('system:terminal','tennis'),('system:tinty','tinty')]:
            for suffix in ['',':update']:
                recipe=next(r for r in recipes if r['id']==ident+suffix)
                self.assertIn('TJIKUP_TERMINAL_TOOL='+tool,recipe['apply'])
                self.assertEqual(recipe['display']['icon'],tool.title())

    def test_migration_precedes_systemd_file_replacement(self):
        recipes=json.loads((ROOT/'tjikup/recipes.json').read_text())['recipes']
        self.assertIn('home:migrate-sync-units',next(r for r in recipes if r['id']=='home:files')['needs'])
        entries=json.loads((ROOT/'native/home/files.json').read_text())
        for name in ['backup-packages','private-backup','private-sync','cloudflare-restic-backup']:
            for suffix in ['.timer','.service']:
                entry=next(e for e in entries if e['path'].endswith('/'+name+suffix))
                self.assertEqual(entry['kind'],'absent')

    def test_activation_and_runtime_have_one_reporting_owner(self):
        recipes=json.loads((ROOT/'tjikup/recipes.json').read_text())['recipes']
        refresh=next(r for r in recipes if r['id']=='home:services')
        for app in ['notjik','bartjik']:
            self.assertIn(app+'.service',refresh['apply'])
            activation=next(r for r in recipes if r['id']=='home:activate:'+app)
            self.assertTrue(any('activate-managed-service.py' in v for v in activation['apply']))
