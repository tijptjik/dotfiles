"""Render real recipes and exercise fleet ordering with only synthetic commands."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import tjikup_support

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = Path(os.environ.get('TJIKUP_TEST_SYSTEM_REPO', str(ROOT / 'system')))
BINARY = Path(os.environ.get('TJIKOS_REPO', str(Path.home()/'code/tjikos'))) / 'apps/tjikup/target/debug/tjikup'

class RecipeTests(unittest.TestCase):
    def documents(self):
        return [json.loads(p.read_text()) for p in [ROOT/'tjikup.json',ROOT/'tjikup/recipes.json',SYSTEM/'tjikup/recipes.json']]

    def test_capture_commit_is_exact_and_complete(self):
        policy=next(r['autocommit'] for r in self.documents()[0]['recipes'] if 'autocommit' in r)
        self.assertEqual(set(policy['files']),{p['source'] for p in json.loads((ROOT/'tjikup/capture.json').read_text())})

    @unittest.skipUnless(BINARY.is_file() and shutil.which('fish'), 'build Rust tjikup first')
    def test_all_templates_render_and_parse_for_fi_li_si(self):
        import runpy
        from unittest.mock import patch
        render=runpy.run_path(str(ROOT/'scripts/check-task-templates.py'))['render']
        for host in ['fi','li','si']:
            with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'TJIKUP_BINARY':str(BINARY)}):
                self.assertEqual(len(render(host,directory)),52)

    @unittest.skipUnless(BINARY.is_file(), 'build Rust tjikup first')
    def test_complete_graph_orders_files_preparation_and_final_tasks(self):
        documents=self.documents()
        with tempfile.TemporaryDirectory() as temporary:
            temp=Path(temporary); trace=temp/'trace'; script=temp/'task.py'
            script.write_text('import os,sys\nfrom pathlib import Path\nwith Path(sys.argv[1]).open("a") as f: f.write(sys.argv[2]+"\\n")\n')
            recipes=[]
            for document in documents:
                for recipe in document['recipes']:
                    recipes.append({k:v for k,v in recipe.items() if k in {'id','label','needs','after','resources','interactive','operation','scope','part_of'}})
                    recipes[-1]['apply']=[sys.executable,str(script),str(trace),recipe['id']]
            config={'version':2,'jobs':4,'recipes':recipes}
            filename=temp/'config.json';filename.write_text(json.dumps(config))
            result=subprocess.run([str(BINARY),'--config',str(filename)],env={**os.environ,'XDG_STATE_HOME':str(temp/'state'),'TJIKUP_NOTIFY':'0'},capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            order=trace.read_text().splitlines()
            self.assertEqual(set(order),{r['id'] for r in recipes})
            self.assertEqual(len(order),len(recipes))
            for recipe in recipes:
                for prerequisite in recipe.get('needs',[]) + recipe.get('after',[]):
                    self.assertLess(order.index(prerequisite),order.index(recipe['id']))
            for repository in ['home','tjikos']:
                self.assertLess(order.index('repo:'+repository+':push'),order.index('home:files'))
            self.assertLess(order.index('home:services'),order.index('system:apps'))
            updates = [r['id'] for r in recipes if r.get('operation') == 'update']
            early = [r['id'] for r in recipes if r.get('operation') != 'update']
            self.assertLess(max(order.index(r) for r in early), min(order.index(r) for r in updates))
            self.assertLess(order.index('home:services'),order.index('system:tailscale'))
            self.assertEqual(order[-1],'system:release')
