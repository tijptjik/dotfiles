"""Runner contracts with synthetic homes and fake service/dependency commands."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / 'native/home/files'


class RemoteRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.bin = self.home / '.local/bin'
        self.bin.mkdir(parents=True)
        for name in ('dev-runner-worker', 'dev-check', 'dev-remote'):
            shutil.copy2(FILES / '.local/bin' / name, self.bin / name)
        shutil.copytree(FILES / '.local/share/dev-runner', self.home / '.local/share/dev-runner')
        self.env = {**os.environ, 'HOME': str(self.home), 'XDG_RUNTIME_DIR': str(self.home),
                    'XDG_STATE_HOME': str(self.home / 'state'),
                    'PATH': str(self.bin) + ':' + os.environ['PATH']}
        self.env.pop('DOTJIK_DEV_CHECK', None)
        self.script('systemctl', 'exit 3')
        self.script('journalctl', 'exit 0')

    def script(self, name, body):
        p = self.bin / name
        p.write_text('#!/usr/bin/env bash\nset -eu\n' + body + '\n')
        p.chmod(0o755)

    def worker(self, *args):
        return subprocess.run([str(self.bin / 'dev-runner-worker'), *args], env=self.env,
                              capture_output=True, text=True, timeout=5)

    def job(self, job_id='job-test', command=('true',)):
        result = self.worker('prepare', job_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        job = self.home / '.cache/dotjik-runner/jobs' / job_id
        (job / 'command').write_bytes(b'\0'.join(a.encode() for a in command) + b'\0')
        return job

    def test_job_paths_arguments_and_exit(self):
        for value in ('../escape', 'job-a/../../escape', '-bad', 'job-a;touch x'):
            self.assertEqual(self.worker('prepare', value).returncode, 64)
        job = self.job(command=('bash', '-c', 'printf "%s" "$1"; exit 23', '--', 'a b;$(false)'))
        result = self.worker('execute', 'job-test', 'test', '0')
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(result.stdout, 'a b;$(false)')
        self.assertEqual((job / 'artifacts/exit-code').read_text(), '23\n')
        self.assertNotEqual(self.worker('prepare', 'job-test').returncode, 0)

    def test_service_limits_and_fail_closed(self):
        self.job()
        self.script('systemd-run', 'printf "%s\\n" "$@"; exit 19')
        for kind, limit in [('lint', '4G'), ('test', '4G'), ('chrome', '5G'), ('typecheck', '6G')]:
            result = self.worker('run', 'job-test', kind, '4173')
            self.assertEqual(result.returncode, 19)
            self.assertIn('MemoryMax=' + limit, result.stdout)
            self.assertIn('KillMode=control-group', result.stdout)
            self.assertIn('--slice=app-devrunner.slice', result.stdout)
            self.assertIn('RuntimeMaxSec=65min', result.stdout)

    def test_frozen_install_failure_prevents_execution(self):
        marker = self.home / 'executed'
        job = self.job(command=('touch', str(marker)))
        (job / 'source/package.json').write_text('{}')
        (job / 'source/bun.lock').write_text('{}')
        self.script('bun', 'printf "%s\\n" "$@"; exit 42')
        result = self.worker('execute', 'job-test', 'test', '0')
        self.assertEqual(result.returncode, 42)
        self.assertIn('--frozen-lockfile', result.stdout)
        self.assertIn('--ignore-scripts', result.stdout)
        self.assertFalse(marker.exists())

    def test_remote_and_local_share_lock_and_nested_checks(self):
        ready = self.home / 'ready'
        release = self.home / 'release'
        self.job(command=('bash', '-c', 'touch "$1"; while [[ ! -f $2 ]]; do sleep .02; done',
                          '--', str(ready), str(release)))
        first = subprocess.Popen([str(self.bin / 'dev-runner-worker'), 'execute',
                                  'job-test', 'test', '0'], env=self.env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: first.poll() is None and first.kill())
        deadline = time.monotonic() + 3
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(ready.exists())
        self.script('systemd-run', 'while [[ $1 != -- ]]; do shift; done; shift; exec "$@"')
        marker = self.home / 'second'
        second = subprocess.Popen([str(self.bin / 'dev-check'), 'touch', str(marker)], env=self.env)
        self.addCleanup(lambda: second.poll() is None and second.kill())
        time.sleep(.1)
        self.assertFalse(marker.exists())
        release.touch()
        self.assertEqual(first.wait(timeout=3), 0)
        self.assertEqual(second.wait(timeout=3), 0)
        self.assertTrue(marker.exists())
        self.job('job-nested', ('dev-check', 'true'))
        self.assertEqual(self.worker('execute', 'job-nested', 'test', '0').returncode, 0)

    def test_active_jobs_cannot_be_removed(self):
        job = self.job()
        self.script('systemctl', 'exit 0')
        self.assertEqual(self.worker('remove', 'job-test').returncode, 75)
        self.assertTrue(job.exists())
        self.script('systemctl', 'exit 3')
        self.assertEqual(self.worker('remove', 'job-test').returncode, 0)
        self.assertFalse(job.exists())

    def test_cancellation_records_marker_even_when_service_stop_succeeds(self):
        job = self.job()
        self.script('systemctl', 'exit 0')
        self.assertEqual(self.worker('cancel', 'job-test').returncode, 0)
        self.assertTrue((job / 'artifacts/cancelled').exists())

    def test_submission_snapshot_exclusions_artifacts_and_exit(self):
        self.script('dev-runner-ssh', '''shift
while [[ ${1:-} == -o || ${1:-} == -S || ${1:-} == -R ]]; do
    if [[ $1 == -R ]]; then
        printf '%s\\n' "$2" >> "$HOME/forwards"
        if [[ ! -f $HOME/first-bind ]]; then
            touch "$HOME/first-bind"
            echo 'Error: remote port forwarding failed for listen port 40000' >&2
            exit 255
        fi
    fi
    shift 2
done
cd "$HOME"
if (( $# == 1 )); then exec bash -c "$1"; else exec "$@"; fi''')
        self.script('systemd-run', 'while [[ $1 != -- ]]; do shift; done; shift; exec "$@"')
        repo = self.home / 'repository with spaces'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        (repo / '.gitignore').write_text('ignored\n')
        (repo / 'tracked').write_text('original')
        (repo / 'deleted').write_text('old')
        (repo / '.env').write_text('private')
        subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c',
                        'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
        (repo / 'tracked').write_text('edited')
        (repo / 'deleted').unlink()
        (repo / 'new file').write_text('new')
        (repo / 'ignored').write_text('private')
        command = '''[[ $(cat tracked) == edited && -f 'new file' ]]
[[ ! -e .env && ! -e ignored && ! -e .git && ! -e deleted ]]
printf '%s' "$1" > "$DEV_RUNNER_ARTIFACTS/result"
echo job-output
exit 23'''
        result = subprocess.run([str(self.bin / 'dev-remote'), '--port', '4173', 'test', 'bash', '-ec', command,
                                 '--', 'a b;$(false)'], cwd=repo, env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 23, result.stderr + result.stdout)
        results = list((self.home / 'state/dev-runner/results').glob('job-*'))
        self.assertEqual(len(results), 1)
        forwards = (self.home / 'forwards').read_text().splitlines()
        self.assertEqual(len(forwards), 2)
        low, high = map(int, Path('/proc/sys/net/ipv4/ip_local_port_range').read_text().split())
        for forward in forwards:
            self.assertTrue(low <= int(forward.split(':')[1]) <= high)
        self.assertIn('retrying', result.stderr)

        self.assertEqual((results[0] / 'artifacts/result').read_text(), 'a b;$(false)')
        self.assertIn('job-output', (results[0] / 'runner.log').read_text())
        self.assertEqual(list((self.home / '.cache/dotjik-runner/jobs').iterdir()), [])

    def test_status_distinguishes_queued_running_and_inactive(self):
        job = self.job()
        (job / 'state').write_text('queued test 100\n')
        self.script('systemctl', 'exit 0')
        result = self.worker('status')
        self.assertIn('queued', result.stdout)
        (job / 'state').write_text('running chrome 100\n')
        self.assertIn('running', self.worker('status').stdout)
        self.script('systemctl', 'exit 3')
        self.assertIn('inactive/running', self.worker('status').stdout)

    def test_outcomes_distinguish_oom_cancellation_and_failure(self):
        for suffix, log, code, cancelled, expected in (
            ('oom', "Failed with result 'oom-kill'.", 137, False, 'oom-kill'),
            ('failed', 'Failed with result exit-code.', 23, False, 'failed'),
            ('exit75', '', 75, False, 'failed'),
            ('cancel', '', 0, True, 'cancelled'),
        ):
            job = self.job('job-' + suffix)
            if cancelled:
                (job / 'artifacts/cancelled').touch()
            self.script('journalctl', 'printf "%s\\n" "$FAKE_JOURNAL"')
            self.script('systemd-run', 'exit ' + str(code))
            self.env['FAKE_JOURNAL'] = log
            result = self.worker('run', 'job-' + suffix, 'typecheck', '0')
            self.assertEqual(result.returncode, 130 if cancelled else code)
            self.assertIn('outcome=' + expected, (job / 'artifacts/outcome.txt').read_text())
            self.assertIn('memory_max=6G', (job / 'artifacts/outcome.txt').read_text())
