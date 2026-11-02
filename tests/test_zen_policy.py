"""Zen startup regression and native deployment checks using synthetic state."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'native/home/files/.config/zen/close-last-regular-tab.sys.mjs'


class ZenPolicyTests(unittest.TestCase):
    def test_only_explicit_last_tab_closes_the_active_window(self):
        harness = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
let observer, listener, closed = 0;
const timers = [];
const tab = attrs => ({pinned: !!attrs.pinned, closing: false,
  hasAttribute: key => !!attrs[key]});
const regular = tab({}), pinned = tab({pinned:true});
const win = {gZenWorkspaces:{}, gBrowserInit:{delayedStartupFinished:true},
  gBrowser:{tabs:[regular,pinned],tabContainer:{addEventListener:(name,fn)=>listener=fn}},
  document:{getElementById:()=>({doCommand:()=>closed++})},
  setTimeout:fn=>timers.push(fn)};
const Services = {focus:{activeWindow:win},wm:{getEnumerator:()=>[win]},
  obs:{addObserver:value=>observer=value}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{Services});
const fire = detail => {listener({target:regular,detail});while(timers.length)timers.shift()();};
const user = {metricsContext:{isUserTriggered:true}};
fire({}); // Startup/internal cleanup of the last ordinary tab.
fire({metricsContext:{isUserTriggered:false}});
assert.equal(closed,0,'startup cleanup must never close the window');
win.gBrowser.tabs.push(tab({}));fire(user);
assert.equal(closed,0,'other ordinary tabs must survive');
win.gBrowser.tabs.pop();
Services.focus.activeWindow={};fire(user);
assert.equal(closed,0,'other synced windows must survive');
Services.focus.activeWindow=win;
fire({...user,adoptedBy:{}});
assert.equal(closed,0,'moving a tab is not closing it');
win.gBrowser.tabs.push(tab({'zen-essential':true}),tab({'zen-empty-tab':true}));
fire(user);assert.equal(closed,1,'explicit final regular tab close must close the window');
listener({target:regular,detail:user});win.gBrowser.tabs.push(tab({}));
while(timers.length)timers.shift()();
assert.equal(closed,1,'a newly opened tab must prevent deferred window closure');
'''
        result = subprocess.run(['node', '-e', harness, str(MODULE)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_zen_files_apply_idempotently_for_each_host(self):
        binary = os.environ.get('TJIKUP_BINARY', str(Path.home() / 'code/tjikos/apps/tjikup/target/debug/tjikup'))
        for host in ['fi', 'li', 'si']:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                home = json.loads((ROOT / f'native/home/files-{host}.json').read_text())
                home_entries = [e for e in json.loads((ROOT / 'native/home/files.json').read_text()) if e.get('group') == 'zen']
                system = json.loads((ROOT / f'system/native/{host}/manifest.json').read_text())
                system_entries = [e for e in system['entries'] if e.get('group') == 'zen']
                self.assertEqual(len(home_entries), 1)
                self.assertEqual(len(system_entries), 2)
                for scope, entries, context, source in [
                    ('home', home_entries, home['context'], ROOT / 'native/home'),
                    ('system', system_entries, system['context'], ROOT / f'system/native/{host}'),
                ]:
                    policy = tmp / scope
                    policy.mkdir()
                    for entry in entries:
                        target = policy / entry['source']
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source / entry['source'], target)
                        entry['uid'], entry['gid'] = os.getuid(), os.getgid()
                    manifest = {'version':1, 'id':f'zen-{scope}-{host}', 'context':context, 'entries':entries}
                    path = policy / 'manifest.json'
                    path.write_text(json.dumps(manifest))
                    destination = policy / 'root'
                    destination.mkdir()
                    command = [binary, 'files', 'apply', '--manifest', str(path), '--state-dir', str(policy/'state'), '--root', str(destination)]
                    for attempt in range(2):
                        result = subprocess.run(command, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        if attempt:
                            self.assertIn('SKIP: 0 changed,', result.stdout)
                self.assertEqual((tmp/'home/root'/home['context']['user']['home'].lstrip('/')/'.config/zen/close-last-regular-tab.sys.mjs').read_bytes(), MODULE.read_bytes())
        loaders = [(ROOT/f'system/native/{host}/files/zen/config.js').read_bytes() for host in ['fi','li','si']]
        self.assertTrue(all(loader == loaders[0] for loader in loaders))


if __name__ == '__main__':
    unittest.main()
