"""Test user-context dispatch and COPR selection without package changes."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class DesktopUserTests(unittest.TestCase):
    def test_root_dispatches_to_desktop_user_with_correct_home_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, body in {
                'id': 'if [ "$#" = 1 ]; then echo 0; else echo 1000; fi',
                'getent': 'printf "desktop:x:1000:1000::%s:/bin/fish\\n" "$TEST_HOME"',
                'sudo': 'printf "%s\\n" "$@"; cat >/dev/null',
            }.items():
                path = root/name
                path.write_text('#!/bin/sh\n'+body+'\n')
                path.chmod(0o755)
            script = root/'hook.fish'
            script.write_text((REPO/'../native/helpers/system/desktop-user.fish').read_text()+'\necho SHOULD_NOT_RUN_AS_ROOT\n')
            result = subprocess.run(['fish', '--no-config', str(script)],
                env={**os.environ, 'PATH':f'{root}:/usr/bin:/bin', 'SUDO_USER':'desktop', 'TEST_HOME':tmp},
                capture_output=True,text=True,check=True)
            self.assertIn('-u\ndesktop\n', result.stdout)
            self.assertIn(f'XDG_CONFIG_HOME={tmp}/.config', result.stdout)
            self.assertIn('/usr/bin/fish', result.stdout)
            self.assertNotIn('SHOULD_NOT_RUN_AS_ROOT', result.stdout)

    def test_root_without_desktop_user_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'id').write_text('#!/bin/sh\necho 0\n');(root/'id').chmod(0o755)
            result=subprocess.run(['fish','--no-config',str(REPO/'../native/helpers/system/desktop-user.fish')],
                env={**os.environ,'PATH':f'{root}:/usr/bin:/bin','SUDO_USER':'root'},capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertIn('Cannot identify',result.stderr)


class CoprTests(unittest.TestCase):
    def test_native_target_is_required_before_install(self):
        text=(REPO/'../native/tasks/system/run_10-install-copr-repos.fish.j2').read_text()
        function=text[text.index('function enable_copr'):text.index('# Retire the font COPR')]
        for available in (True,False):
            harness='''
function is_copr_configured; return 1; end
function copr_native_chroot; %s; end
function rpm; echo 45; end
function uname; echo x86_64; end
function status_msg; printf 'ROW %%s\\n' (string join '|' -- $argv); end
function step_run_note_quiet; printf 'RUN %%s\\n' (string join '|' -- $argv); end
''' % ('echo fedora-45-x86_64' if available else 'return 1')
            result=subprocess.run(['fish','--no-config','-c',harness+function+'\nenable_copr purian23/material-symbols-fonts'],capture_output=True,text=True)
            if available:
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertNotIn('FAILED',result.stdout)
                self.assertIn('|fedora-45-x86_64',result.stdout)
                self.assertEqual(result.stdout.count('RUN '),1)
            else:
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn('RUN ',result.stdout)

    def test_only_native_release_can_be_selected(self):
        text = (REPO/'../native/tasks/system/run_10-install-copr-repos.fish.j2').read_text()
        function = text[text.index('function copr_native_chroot'):text.index('# Enable only')]
        for targets, expected in [(['fedora-43-x86_64'], None),
                                  (['fedora-43-x86_64', 'fedora-45-x86_64'], 'fedora-45-x86_64'),
                                  (['fedora-45-aarch64'], None)]:
            with self.subTest(targets=targets):
                payload = json.dumps({'chroot_repos': dict.fromkeys(targets, {})})
                harness = "function rpm; echo 45; end\nfunction uname; echo x86_64; end\n"
                harness += "function curl; printf '%s' '" + payload + "'; end\n"
                result = subprocess.run(['fish', '--no-config', '-c',
                    harness + function + '\ncopr_native_chroot example/project'],
                    capture_output=True, text=True)
                if expected:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), expected)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, '')

    def test_disabled_configured_repo_is_recognized_exactly(self):
        text = (REPO/'../native/tasks/system/run_10-install-copr-repos.fish.j2').read_text()
        function = text[text.index('function is_copr_configured'):text.index('function copr_native_chroot')]
        for suffix, found in [('', True), (' (disabled)', True), ('-other', False)]:
            with self.subTest(suffix=suffix):
                harness = "function dnf; echo 'copr.fedorainfracloud.org/example/project" + suffix + "'; end\n"
                result = subprocess.run(['fish', '--no-config', '-c',
                    harness + function + '\nis_copr_configured example/project'],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, found, result.stderr)

    def test_quiet_success_hides_command_output_but_failure_reveals_it(self):
        status=(REPO/'../native/helpers/system/status.fish').read_text()
        logging=(REPO/'../native/tasks/assets/system/templates/fish_logging.fish').read_text()
        for code in (0,7):
            script=status+'\n'+logging+"\nsetup_logging test\nstep_run_note_quiet 'COPR test' 'using fedora-43-x86_64' sh -c 'echo noisy-output; exit "+str(code)+"'"
            result=subprocess.run(['fish','--no-config','-c',script],env={**os.environ,'TJIKUP_NO_SPIN':'1','TJIKUP_COLOR':'0'},capture_output=True,text=True)
            self.assertEqual(result.returncode,code,result.stderr)
            if code:
                self.assertIn('noisy-output',result.stdout)
                self.assertIn('FAILED',result.stdout)
            else:
                self.assertNotIn('noisy-output',result.stdout)
                self.assertIn('using fedora-43-x86_64',result.stdout)


class ClientPackagePolicyTests(unittest.TestCase):
    def test_bartjik_font_has_no_system_package_or_copr_dependency(self):
        policy = (REPO / '../native/tasks/assets/system/data/packages.json').read_text()
        self.assertNotIn("'material-symbols-fonts'", policy)
        self.assertNotIn("'purian23/material-symbols-fonts'", policy)

    def test_retired_azahar_is_not_requested_for_reinstallation(self):
        policy = (REPO / '../native/tasks/assets/system/data/packages.json').read_text()
        self.assertNotIn("'org.azahar_emu.Azahar'", policy)
