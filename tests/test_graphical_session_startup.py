"""Headless apply must not activate graphical-session.target indirectly."""
import os
from pathlib import Path
import subprocess
import unittest

REPO=Path(__file__).resolve().parents[1]


class GraphicalStartupTests(unittest.TestCase):
    def test_only_running_wayland_session_starts_helpers(self):
        text=(REPO/'home/.chezmoiscripts/run_after_99-systemd-reload.fish.tmpl').read_text()
        function=text[text.index('function configure_client_user_units'):text.index('if user_units_need_reload; or units_need_enable_now $client_services')]
        harness='''
function systemctl
    if contains -- is-active $argv
        test "$SESSION_ACTIVE" = 1
        return $status
    end
    if contains -- show-environment $argv
        if test "$HAS_DISPLAY" = 1; echo WAYLAND_DISPLAY=wayland-1; end
        return 0
    end
    echo (string join ' ' -- $argv)
    if contains -- start $argv; return $START_STATUS; end
end
function status_msg; echo (string join ' ' -- $argv); end
'''
        for active,display in [('0','0'),('0','1'),('1','0'),('1','1')]:
            with self.subTest(active=active,display=display):
                result=subprocess.run(['fish','--no-config','-c',harness+function+'\nconfigure_client_user_units hyprpaper.service'],env={**os.environ,'SESSION_ACTIVE':active,'HAS_DISPLAY':display,'START_STATUS':'7'},text=True,capture_output=True,timeout=5)
                self.assertIn('--user enable hyprpaper.service',result.stdout)
                should_start=active==display=='1'
                self.assertEqual('--user start hyprpaper.service' in result.stdout,should_start)
                self.assertEqual(result.returncode,7 if should_start else 0)

    def test_lock_helper_cannot_pull_in_session(self):
        for path in ['hyprlock-login.service.tmpl']:
            text=(REPO/'home/dot_config/systemd/user'/path).read_text()
            self.assertNotIn('\nWants=graphical-session.target',text)
            self.assertNotIn('\nRequires=graphical-session.target',text)
            self.assertIn('PartOf=graphical-session.target',text)
