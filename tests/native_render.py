"""Synthetic template rendering through the same Rust engine used in production."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
ROOT=Path(__file__).resolve().parents[1]
BINARY=os.environ.get('TJIKUP_BINARY', str(Path.home()/'code/tjikos/apps/tjikup/target/debug/tjikup'))
os.environ['PATH']=str(ROOT/'tests/bin')+os.pathsep+os.environ['PATH']

def main():
    args=sys.argv[1:]
    config_path=Path(args[args.index('--config')+1]) if '--config' in args else None
    config=(tomllib.loads(config_path.read_text()) if config_path.suffix=='.toml' else json.loads(config_path.read_text())) if config_path else {}
    data=config.get('data',{})
    desktop=data.get('isDesktop', data.get('isClient',not data.get('isLaptop',False) and not data.get('isServer',False)))
    laptop=data.get('isLaptop',False)
    host='li' if laptop else 'fi' if desktop else 'si'
    context={'hostname':host,'role':{'fi':'desktop','li':'laptop','si':'server'}[host],
             'is_desktop':desktop,'is_laptop':laptop,'is_server':host=='si','is_client':host!='si',
             'repo_dir':str(ROOT),'home_source':str(ROOT/'native/home'),'system_source':str(ROOT/'system/native'),
             'user':{'name':'io','home':os.environ.get('HOME','/home/io')},'os':'linux'}
    source=Path(args[args.index('-f')+1]) if '-f' in args else None
    system='/system/' in str(source) or ('--source' in args and args[args.index('--source')+1].endswith('/system'))
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        if source is None:
            source=root/'template.j2'
            source.write_text(sys.stdin.read())
        inputs=json.loads((ROOT/'native/tasks'/('system.json' if system else 'home.json')).read_text())
        (root/'data.json').write_bytes((ROOT/'native/tasks/data.json').read_bytes())
        inputs['context_files']=['data.json']
        for key, source_path in list(inputs.get('includes',{}).items()):
            target=root/source_path
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((ROOT/'native/tasks'/source_path).read_bytes())
        inputs['context']=context
        (root/'inputs.json').write_text(json.dumps(inputs))
        output=root/'rendered'
        graph={'version':2,'recipes':[{'id':'render','render':{'native':str(root/'inputs.json'),'templates':[{'name':'rendered','source':str(source),'syntax':['true','{script}']}] }},
          {'id':'collect','needs':['render'],'apply':['cp','{run_dir}/rendered',str(output)]}]}
        (root/'config.json').write_text(json.dumps(graph))
        result=subprocess.run([BINARY,'--config',str(root/'config.json')],capture_output=True,env={**os.environ,'XDG_STATE_HOME':str(root/'state'),'XDG_CACHE_HOME':str(root/'cache'),'TJIKUP_NOTIFY':'0'})
        if result.returncode:
            sys.stderr.buffer.write(result.stdout+result.stderr)
            for log in (root/'state').rglob('*.log'):sys.stderr.buffer.write(log.read_bytes())
            return result.returncode
        sys.stdout.buffer.write(output.read_bytes())
    return 0
if __name__=='__main__':sys.exit(main())
