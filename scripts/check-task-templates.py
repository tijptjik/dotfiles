#!/usr/bin/env python3
"""Render and syntax-check maintenance recipes for all fleet roles; never execute tasks."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def render(host, directory, repo=ROOT):
    role = {'fi':'desktop','li':'laptop','si':'server'}[host]
    context = {'hostname':host,'role':role,'is_client':role!='server',
               'is_desktop':role=='desktop','is_laptop':role=='laptop','is_server':role=='server',
               'home_source':str(repo/'home'),'system_source':str(repo/'system/etc'),
               'user':{'name':'io','home':'/home/io'},'os':'linux'}
    directory = Path(directory)
    context_path = directory/'context.json'
    context_path.write_text(json.dumps(context))
    recipes = []
    for name in ['tjikup/recipes.json','system/tjikup/recipes.json']:
        for recipe in json.loads((repo/name).read_text())['recipes']:
            if 'render' not in recipe:
                continue
            batch = recipe['render']
            batch['context_command'] = ['cat',str(context_path)]
            recipes.append({'id':recipe['id'],'render':batch})
    batches = list(recipes)
    output = directory/'rendered'
    recipes.append({'id':'collect','needs':[recipe['id'] for recipe in batches],
                    'apply':['python3','-c','import shutil,sys; shutil.copytree(sys.argv[1],sys.argv[2])','{run_dir}',str(output)]})
    config = directory/'config.json' 
    config.write_text(json.dumps({'version':2,'env':{'DOTJIK_REPO':str(repo)},'recipes':recipes}))
    binary = os.environ.get('TJIKUP_BINARY',str(Path.home()/'.local/bin/tjikup'))
    result = subprocess.run([binary,'--config',str(config)],capture_output=True,text=True,
                            env={**os.environ,'XDG_STATE_HOME':str(directory/'state'),'TJIKUP_NOTIFY':'0'})
    if result.returncode:
        raise RuntimeError(f'Native task rendering failed for {host}; inspect template syntax and context')
    run = output
    return {template['name']:(run/template['name']).read_text()
            for recipe in batches for template in recipe['render']['templates']}


if __name__ == '__main__':
    for host in ['fi','li','si']:
        with tempfile.TemporaryDirectory(prefix='tjikup-template-check-') as directory:
            scripts = render(host, directory)
            print(f'{host}: {len(scripts)} native scripts rendered and syntax-checked')
