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
        from fleet_capture import discover_propagators
        policy=next(r['autocommit'] for r in self.documents()[0]['recipes'] if 'autocommit' in r)
        self.assertEqual(set(policy['files']),{str(p.source) for p in discover_propagators()})

    @unittest.skipUnless(shutil.which('chezmoi') and shutil.which('fish'), 'render tools required')
    def test_all_templates_render_and_parse_for_fi_li_si(self):
        for root,component in [(ROOT,'home'),(SYSTEM,'etc')]:
            directory=root/component/'.chezmoitemplates/tjikup'
            self.assertTrue(directory.is_dir())
            self.assertFalse(set(p.name for p in directory.iterdir()) & set(p.name for p in (root/component/'.chezmoiscripts').iterdir()))
            for host in ['fi','li','si']:
                with tempfile.TemporaryDirectory() as temporary:
                    temp=Path(temporary);config=temp/'config.json'
                    config.write_text(json.dumps({'data':{'isDesktop':host=='fi','isLaptop':host=='li','isClient':host!='si','isServer':host=='si','hostname':host}}))
                    for source in directory.iterdir():
                        with self.subTest(host=host,recipe=source.name):
                            text=source.read_text().replace('.chezmoi.hostname',json.dumps(host))
                            if source.suffix=='.tmpl':
                                text=subprocess.check_output(['chezmoi','--source',str(root/component),'--config',str(config),'--persistent-state',str(temp/'state.db'),'execute-template'],input=text,text=True)
                            if '.py' in source.name:
                                compile(text,source.name,'exec')
                            else:
                                result=subprocess.run(['fish','--no-config','--no-execute'],input=text,text=True,capture_output=True)
                                self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(BINARY.is_file(), 'build Rust tjikup first')
    def test_complete_graph_orders_files_preparation_and_final_tasks(self):
        documents=self.documents()
        with tempfile.TemporaryDirectory() as temporary:
            temp=Path(temporary); trace=temp/'trace'; script=temp/'task.py'
            script.write_text('import os,sys\nfrom pathlib import Path\nwith Path(sys.argv[1]).open("a") as f: f.write(sys.argv[2]+"\\n")\n')
            recipes=[]
            for document in documents:
                for recipe in document['recipes']:
                    recipes.append({k:v for k,v in recipe.items() if k in {'id','label','needs','after','resources','interactive'}})
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
            self.assertLess(order.index('system:apps'),order.index('home:services'))
            self.assertLess(order.index('home:services'),order.index('system:tailscale'))
            self.assertEqual(order[-1],'system:release')
