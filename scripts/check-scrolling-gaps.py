#!/usr/bin/env python3
"""Native regression probe. Requires an empty disposable compositor, never the desktop.

Usage: python3 scripts/check-scrolling-gaps.py --instance SIGNATURE --plugin FILE
The specified compositor is closed after the test. Test artifacts go to --artifacts.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--instance', required=True)
parser.add_argument('--plugin', required=True, type=Path)
parser.add_argument('--artifacts', required=True, type=Path)
args = parser.parse_args()
if args.instance == os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
    parser.error('refusing to use the current desktop compositor')
instances = json.loads(subprocess.check_output(['hyprctl', 'instances', '-j'], text=True))
instance = next(i for i in instances if i['instance'] == args.instance)
env = dict(os.environ, HYPRLAND_INSTANCE_SIGNATURE=instance['instance'], WAYLAND_DISPLAY=instance['wl_socket'])
args.artifacts.mkdir(parents=True, exist_ok=True)
def ctl(*values):
    result = subprocess.run(['hyprctl', *values], env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'hyprctl {values}: {result.stdout} {result.stderr}')
    return result.stdout
def evaluate(code):
    assert ctl('eval', code).strip() == 'ok'
def focus(address):
    evaluate('hl.dispatch(hl.dsp.focus({window="address:' + address + '"}))')
if json.loads(ctl('-j', 'clients')):
    parser.error('the disposable compositor must have no existing clients')
(args.artifacts / 'panel.json').write_text(json.dumps({
    'layer': 'top', 'position': 'top', 'height': 24, 'exclusive': True,
    'modules-left': ['custom/probe'], 'custom/probe': {'format': 'PANEL REMAINS VISIBLE'}}))
(args.artifacts / 'panel.css').write_text('window#waybar {background:#00aa99;color:white;} * {font-family:monospace;font-size:14px;}')
procs=[]
try:
    assert not ctl('configerrors').strip()
    print(ctl('plugin','load',str(args.plugin.resolve())),flush=True)
    time.sleep(.4)
    originals=json.loads(ctl('-j','monitors'))
    print(ctl('output','create','headless','SLIDES-PROBE'),flush=True)
    evaluate('hl.monitor({output="SLIDES-PROBE",mode="1000x680@60",position="0x0",scale=1})')
    for mon in originals: evaluate('hl.monitor({output='+json.dumps(mon['name'])+',disabled=true})')
    time.sleep(.3)
    evaluate('hl.dispatch(hl.dsp.focus({monitor="SLIDES-PROBE"})); hl.dispatch(hl.dsp.focus({workspace=91}))')
    for n in range(3):
        procs.append(subprocess.Popen(['kitty','--config','NONE','--class','slides-probe','--title',f'slides-{n}','-o','remember_window_size=no','-o','linux_display_server=wayland','sh','-c','sleep 120'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        for _ in range(60):
            clients=json.loads(ctl('-j','clients'))
            if len(clients)==n+1: break
            time.sleep(.1)
        else:
            raise RuntimeError('test terminal did not map')
    a,b,c=[x['address'] for x in sorted(clients,key=lambda x:x['at'][0])]
    def snap():
        time.sleep(.3)
        return {x['address']:x for x in json.loads(ctl('-j','clients'))}
    panel=subprocess.Popen(['/usr/bin/waybar','-c',str(args.artifacts / 'panel.json'),'-s',str(args.artifacts / 'panel.css')],env=env,stdout=subprocess.DEVNULL,stderr=open(str(args.artifacts / 'panel.log'),'w'))
    procs.append(panel)
    time.sleep(.8)
    focus(a);evaluate('hl.dispatch(hl.dsp.layout("colresize 1"))');time.sleep(1)
    baseline=snap()
    frames=[]
    for turn in range(4):
        evaluate('hl.dispatch(hl.dsp.layout("focus '+('r' if turn%2==0 else 'l')+'"))')
        for frame in range(24):
            state={x['address']:x for x in json.loads(ctl('-j','clients'))}
            for neighbor in (b,c):
                assert state[neighbor]['size']==baseline[neighbor]['size'],(turn,frame,neighbor,state[neighbor]['size'],baseline[neighbor]['size'])
            assert all(x['fullscreen']==0 and x['fullscreenClient']==0 for x in state.values())
            rendered={x['address']:x for x in json.loads(ctl('scrolling-gaps:state'))}
            for neighbor in (b,c):
                assert all(abs(x-y)<.01 for x,y in zip(rendered[neighbor]['current'],baseline[neighbor]['size'])),rendered[neighbor]
            frames.append({'turn':turn,'frame':frame,'wide':rendered[a]['current'],'ordinary':rendered[b]['current']})
            if frame==6 and turn==0:
                subprocess.run(['grim',str(args.artifacts / 'mid-transition.png')],env=env,check=True)
            time.sleep(.025)
    assert len({tuple(f['wide']) for f in frames})>2, 'expected animated intermediate sizes'
    (args.artifacts / 'animation-frames.json').write_text(json.dumps(frames,indent=2))
    subprocess.run(['grim',str(args.artifacts / 'focused-gapless.png')],env=env,check=True)
    print('PASS: 96 animation samples, ordinary sizes invariant, only wide window animates, fullscreen always zero',flush=True)
    print('monitor reservations:',[(m['reserved']) for m in json.loads(ctl('-j','monitors'))],flush=True)
    print('wide animation sizes:',len({tuple(f['wide']) for f in frames}),flush=True)
    # Floating clients must remain visible while the wide column is gapless.
    focus(c);evaluate('hl.dispatch(hl.dsp.window.float({action="set"}))')
    time.sleep(.7)
    float_before=snap()[c]
    focus(a);time.sleep(.7)
    float_after=snap()[c]
    assert float_after['floating'] and not float_after['hidden']
    assert float_after['size']==float_before['size']
    assert float_after['fullscreen']==0 and float_after['fullscreenClient']==0
    # Special workspaces must not resize the normal strip beneath them.
    evaluate('hl.dispatch(hl.dsp.window.move({workspace="special:gap-probe",follow=false,window="address:'+c+'"}))')
    focus(a);time.sleep(.7)
    underlying={w['address']:w for w in json.loads(ctl('scrolling-gaps:state'))}
    for opening in (True,False,True,False):
        evaluate('hl.dispatch(hl.dsp.workspace.toggle_special("gap-probe"))')
        for _ in range(20):
            current={w['address']:w for w in json.loads(ctl('scrolling-gaps:state'))}
            assert current[a]['gapless']
            for addr in (a,b):
                assert current[addr]['goal']==underlying[addr]['goal']
                assert all(abs(x-y)<.01 for x,y in zip(current[addr]['current'],underlying[addr]['current']))
            assert not current[c]['gapless']
            time.sleep(.02)
    print('PASS: special workspace open/close preserves underlying rendered geometry',flush=True)
    # Leaving the monitor must retain its last-focused column's geometry.
    ctl('output', 'create', 'headless', 'OTHER-PROBE')
    evaluate('hl.monitor({output="OTHER-PROBE",mode="800x600@60",position="1000x0",scale=1})')
    time.sleep(.5)
    evaluate('hl.workspace_rule({workspace="92",monitor="OTHER-PROBE"}); hl.dispatch(hl.dsp.focus({monitor="OTHER-PROBE"})); hl.dispatch(hl.dsp.focus({workspace=92}))')
    time.sleep(.3)
    procs.append(subprocess.Popen(['kitty','--config','NONE','--class','slides-probe',
        '--title','other-monitor','-o','linux_display_server=wayland','sh','-c','sleep 120'],
        env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    for _ in range(60):
        other=next((w for w in json.loads(ctl('-j','clients')) if w['title']=='other-monitor'),None)
        if other: break
        time.sleep(.1)
    assert other, 'second monitor terminal did not map'
    assert other['workspace']['id']==92, other
    d=other['address']
    focus(d); evaluate('hl.dispatch(hl.dsp.layout("colresize 1"))')
    time.sleep(.5)
    for address in (a,d,a,d):
        focus(address)
        for _ in range(12):
            current={w['address']:w for w in json.loads(ctl('scrolling-gaps:state'))}
            assert current[a]['gapless'] and current[d]['gapless'], current
            assert current[a]['goal']==underlying[a]['goal']
            assert all(abs(x-y)<.01 for x,y in zip(current[a]['current'],underlying[a]['current']))
            time.sleep(.025)
    ctl('plugin','unload',str(args.plugin.resolve()))
    ctl('plugin','load',str(args.plugin.resolve()))
    time.sleep(.5)
    current={w['address']:w for w in json.loads(ctl('scrolling-gaps:state'))}
    assert current[a]['gapless'] and current[d]['gapless'], current
    subprocess.run(['grim','-o','SLIDES-PROBE',str(args.artifacts / 'unfocused-monitor.png')],env=env,check=True)
    print('PASS: cross-monitor focus and plugin reload preserve both gapless columns',flush=True)
    # A stack must remain gapped, even when its column width is 100%.
    focus(b);evaluate('hl.dispatch(hl.dsp.window.move({direction="l"}))')
    time.sleep(.7)
    state=json.loads(ctl('scrolling-gaps:state'))
    assert not any(w['gapless'] for w in state if w['address'] != d)
    print('PASS: floating visibility and stacked-column exclusion',flush=True)
    print(ctl('plugin','unload',str(args.plugin.resolve())),flush=True)
finally:
    for p in procs: p.terminate()
    ctl('dispatch','hl.dsp.exit()')
