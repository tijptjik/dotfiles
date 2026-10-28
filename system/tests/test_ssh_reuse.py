"""Check OpenSSH's effective reuse policy without opening connections."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'etc/ssh/ssh_config.d/10-connection-reuse.conf'


@unittest.skipUnless(shutil.which('ssh'), 'OpenSSH required')
class SshReuseTests(unittest.TestCase):
    def effective(self, host, *options, prefix=''):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / 'config'
            config.write_text(prefix + '\nInclude ' + str(POLICY) + '\n')
            result = subprocess.run(['ssh', '-G', '-F', str(config), *options, host],
                                    capture_output=True, text=True, check=True)
            return dict(line.split(' ', 1) for line in result.stdout.splitlines())

    def test_git_and_fleet_destinations_share_defaults(self):
        for host in ('git@github.com', 'io@fi.local', 'io@li.local', 'm@ssh.type.hk'):
            with self.subTest(host=host):
                config = self.effective(host)
                self.assertEqual(config['controlmaster'], 'auto')
                self.assertEqual(config['controlpersist'], '300')
                self.assertTrue(config['controlpath'].startswith(str(Path.home() / '.ssh/cm-')))

    def test_socket_separates_destinations_users_ports_and_jump_hosts(self):
        paths = [self.effective(host, *options)['controlpath'] for host, options in (
            ('git@github.com', ()),
            ('other@github.com', ()),
            ('git@elsewhere.example', ()),
            ('git@github.com', ('-p', '2222')),
            ('git@github.com', ('-J', 'bastion.example')),
        )]
        self.assertEqual(len(set(paths)), len(paths))

    def test_user_configuration_can_disable_reuse(self):
        config = self.effective('git@github.com', prefix=(
            'Host github.com\n    ControlMaster no\n'
            '    ControlPath none\n    ControlPersist no\n'))
        self.assertEqual(config['controlmaster'], 'false')
        self.assertEqual(config['controlpersist'], 'no')
        self.assertNotIn('controlpath', config)

    def test_supervised_connections_can_bypass_existing_master(self):
        config = self.effective('io@li.local', '-o', 'ControlMaster=no',
                                '-o', 'ControlPath=none')
        self.assertEqual(config['controlmaster'], 'false')
        self.assertNotIn('controlpath', config)


if __name__ == '__main__':
    unittest.main()
