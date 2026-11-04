"""Check host policy and shortcut routing without sending clipboard contents."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('lua'), 'Lua required')
class DesktopShortcutTests(unittest.TestCase):
    def test_clipboard_shortcut_passes_through_kitty_and_unfocused_desktop(self):
        script = r'''
local active, calls = nil, {}
hl = {
    get_active_window = function() return active end,
    dsp = {exec_cmd = function(command) return command end},
    dispatch = function(command) table.insert(calls, command) end,
}
local helpers = dofile(arg[1])
assert(helpers.telegram_clipboard_shortcut().pass_event)
for _,window in ipairs({
    {class="kitty"}, {class="Kitty"}, {class="kitty-terminal"},
    {class="custom",initial_class="kitty"},
}) do
    active = window
    assert(helpers.telegram_clipboard_shortcut().pass_event)
end
assert(#calls == 0)
active = {class="org.mozilla.firefox",initial_class="org.mozilla.firefox"}
helpers.telegram_clipboard_shortcut()
assert(#calls == 1)
assert(calls[1] == "$HOME/.local/bin/notjikctl telegram save-clipboard")
-- Every press checks focus again; a later terminal focus never sends a message.
active = {class="kitty"}
assert(helpers.telegram_clipboard_shortcut().pass_event)
assert(#calls == 1)
'''
        subprocess.run(['lua', '-', str(ROOT / 'native/home/files/.config/hypr/helpers.lua')],
                       input=script, text=True, check=True)

    def test_host_shortcuts_and_telegram_policy(self):
        for host in ('fi', 'li', 'si'):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / 'context.json'
                config.write_text(json.dumps({'data': {
                    'isDesktop': host == 'fi', 'isLaptop': host == 'li', 'isServer': host == 'si',
                }}))

                def render(name):
                    return subprocess.check_output([
                        'python3', '-B', str(ROOT / 'tests/native_render.py'),
                        '--config', str(config), '-f', str(ROOT / 'native/home/files/.config' / name),
                    ], text=True)

                bindings = render('hypr/bindings.lua.j2')
                self.assertIn('hl.bind(ctrl("V", "SHIFT"), helpers.telegram_clipboard_shortcut)', bindings)
                self.assertNotIn('hl.bind(super("N")', bindings)
                for key, action in [('slash', 'dismiss'), ('apostrophe', 'primary'), ('semicolon', 'secondary')]:
                    self.assertIn(f'hl.bind(super("{key}"), hl.dsp.exec_cmd("$HOME/.local/bin/notjikctl selected {action}"))', bindings)
                self.assertIn('hl.bind(super("code:9", "CAPS"),', bindings)
                self.assertIn('hl.bind(super("code:9", "CAPS", "CTRL"),', bindings)
                self.assertIn('hl.bind(super("code:9", "CAPS", "SHIFT"),', bindings)
                subprocess.run(['lua', '-'], input='assert(load(' + '[====[' + bindings + ']====]' + '))',
                               text=True, check=True)
                rendered = render('notjik/config.json.j2')
                if host == 'si':
                    self.assertFalse(rendered.strip())
                    continue
                config = json.loads(rendered)
                self.assertEqual(config['history']['excludeApps'], [
                    'Telegram Desktop', 'Telegram via Notjik', 'org.telegram.desktop', 'telegram',
                ])
                self.assertEqual(config['telegram'], {
                    'dismissIsRead': ['@starprowlarr_bot'], 'dismissReadMode': 'safe',
                })
