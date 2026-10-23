"""No live service changes: exercise apply decisions with a stub user manager."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]


class HyprvoiceStartupTests(unittest.TestCase):
    def test_missing_binary_headless_session_and_real_start_failure(self):
        hook=(REPO/'home/.chezmoiscripts/run_after_99-systemd-reload.fish.tmpl').read_text()
        function=hook[hook.index('function configure_hyprvoice_unit'):hook.index('configure_hyprvoice_unit; or exit')]
        harness='''
function systemctl
    if contains -- show-environment $argv
        if test "$MODE" != headless; echo WAYLAND_DISPLAY=wayland-1; end
        return 0
    end
    if contains -- is-active $argv; return 1; end
    if contains -- start $argv
        echo START_ATTEMPT
        return 7
    end
    return 0
end
function status_msg; echo (string join '|' -- $argv); end
function stage_note; $argv[5..]; end
'''
        for mode in ('missing','headless','ready'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                binary=Path(tmp)/'.local/bin/hyprvoice'
                if mode!='missing':
                    binary.parent.mkdir(parents=True);binary.write_text('#!/bin/sh\n');binary.chmod(0o755)
                result=subprocess.run(['fish','--no-config','-c',harness+function+'\nconfigure_hyprvoice_unit'],env={**os.environ,'HOME':tmp,'MODE':mode},capture_output=True,text=True,timeout=5)
                if mode=='ready':
                    self.assertEqual(result.returncode,7,result.stderr)
                    self.assertIn('START_ATTEMPT',result.stdout)
                else:
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertNotIn('START_ATTEMPT',result.stdout)
                    self.assertIn('not installed' if mode=='missing' else 'waiting for Wayland',result.stdout)

    def test_service_uses_session_conditions_without_polling(self):
        unit=(REPO/'home/dot_config/systemd/user/hyprvoice.service').read_text()
        self.assertIn('WantedBy=graphical-session.target',unit)
        self.assertIn('PartOf=graphical-session.target',unit)
        self.assertIn('ConditionEnvironment=WAYLAND_DISPLAY',unit)
        self.assertIn('ConditionFileIsExecutable=%h/.local/bin/hyprvoice',unit)
        self.assertNotIn('ExecStartPre=',unit)
        startup=(REPO/'home/dot_config/hypr/execs.lua.tmpl').read_text()
        self.assertIn('SDL_IM_MODULE && systemctl --user start hyprvoice.service',startup)
