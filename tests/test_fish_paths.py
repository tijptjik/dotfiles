import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATHS = ROOT / 'home/dot_config/fish/conf.d/paths.fish'


@unittest.skipUnless(shutil.which('fish') and shutil.which('git'), 'Fish and Git required')
class FishPathTests(unittest.TestCase):
    def test_project_bins_are_pruned_and_follow_directory_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            repo = home / 'repo'
            worktree = home / 'worktree'
            normal_bin = home / 'normal/bin'
            normal_bin.mkdir(parents=True)
            git_env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
            subprocess.run(['git', 'init', '-q', str(repo)], check=True, env=git_env)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test',
                            '-c', 'user.email=test@example.invalid',
                            'commit', '-qm', 'initial', '--allow-empty'], check=True, env=git_env)
            subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '-qb',
                            'other', str(worktree)], check=True, env=git_env)
            (repo / 'bin').mkdir()
            (worktree / 'bin').mkdir()
            script = '''
set -gx HOME $argv[1]
set -gx XDG_CONFIG_HOME $HOME/.config
set -gx TOOLS $HOME/tools
set -gx CONFIG $HOME/.config
set -gx PYENV_ROOT $HOME/pyenv
set -gx BUN_INSTALL $HOME/bun
set -U fish_user_paths $HOME/repo/bin $HOME/normal/bin
set -gx PATH $HOME/worktree/bin $HOME/repo/bin $HOME/normal/bin $PATH
source $argv[2]
__fish_prune_project_bins
contains -- $HOME/normal/bin $PATH; or exit 10
contains -- $HOME/repo/bin $fish_user_paths; and exit 11
contains -- $HOME/worktree/bin $PATH; and exit 12
cd $HOME/repo
test "$PATH[1]" = "$HOME/repo/bin"; or exit 13
cd $HOME/worktree
test "$PATH[1]" = "$HOME/worktree/bin"; or exit 14
contains -- $HOME/repo/bin $PATH; and exit 15
cd $HOME
contains -- $HOME/worktree/bin $PATH; and exit 16
exit 0
'''
            env = {**os.environ, 'HOME': tmp, 'XDG_CONFIG_HOME': str(home / '.config')}
            subprocess.run(['fish', '--no-config', '-c', script, '--', tmp, str(PATHS)],
                           env=env, cwd=tmp, check=True, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
