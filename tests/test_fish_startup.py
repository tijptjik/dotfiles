import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
UTILS = ROOT / 'native/home/files/.config/fish/conf.d/utils.fish'


@unittest.skipUnless(shutil.which('fish') and shutil.which('git'), 'Fish and Git required')
class FishStartupTests(unittest.TestCase):

    def test_greeting_does_not_start_external_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = '''
source $argv[1]
function docker
    echo unexpected-docker >&2
    return 20
end
function fortune
    echo unexpected-fortune >&2
    return 21
end
fish_greeting
functions -q pony; or exit 22
'''
            result = subprocess.run(['fish', '--no-config', '-c', script, '--', str(UTILS)],
                                    env={**os.environ, 'HOME': tmp, 'XDG_CONFIG_HOME': tmp},
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, '')
            self.assertEqual(result.stderr, '')

    def test_tty_greeting_generates_a_fresh_quote_each_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fortune = root / 'fortune'
            fortune.write_text('#!/bin/sh\nn=0\n[ ! -f "$HOME/count" ] || read -r n < "$HOME/count"\nn=$((n+1))\nprintf "%s\\n" "$n" > "$HOME/count"\nprintf "quote-%s\\n" "$n"\n')
            renderer = root / 'greetjik'
            renderer.write_text('#!/bin/sh\n/bin/cat\n')
            fortune.chmod(0o755)
            renderer.chmod(0o755)
            script = "source $argv[1]; function isatty; return 0; end; fish_greeting; fish_greeting"
            result = subprocess.run(['fish', '--no-config', '-c', script, '--', str(UTILS)],
                                    env={**os.environ, 'HOME': tmp, 'XDG_CONFIG_HOME': tmp,
                                         'PATH': tmp + ':/usr/bin:/bin'},
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.splitlines(), ['quote-1', 'quote-2'])


if __name__ == '__main__':
    unittest.main()
