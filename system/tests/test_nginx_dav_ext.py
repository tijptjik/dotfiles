"""Regressions for interrupted nginx upgrades and incompatible modules."""
from pathlib import Path
import subprocess
import unittest

TEMPLATE = Path(__file__).resolve().parents[1] / "../native/tasks/assets/system/templates/nginx_dav_ext.fish"

class NginxModuleTests(unittest.TestCase):
    def fish(self, body):
        return subprocess.run(["fish", "--no-config", "-c", "source " + str(TEMPLATE) + "\n" + body], text=True, capture_output=True, timeout=10)

    def test_binary_version_wins_over_duplicate_rpm_records(self):
        result = self.fish("""
function nginx; echo 'nginx version: nginx/1.30.5' >&2; end
function rpm; printf '1.30.41.30.5'; end
nginx_dav_ext_current_abi
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "1.30.5")

    def test_matching_dav_does_not_hide_broken_stream_module(self):
        for config_status in (0, 1):
            result = self.fish("""
function nginx; echo 'nginx version: nginx/1.30.5' >&2; end
function rpm; echo '4.fc43.nginx1.30.5'; end
function sudo; return STATUS; end
nginx_dav_ext_is_current
""".replace("STATUS", str(config_status)))
            self.assertEqual(result.returncode, config_status, result.stderr)

    def test_version_prefix_is_not_an_abi_match(self):
        result = self.fish("""
function nginx; echo 'nginx version: nginx/1.30.5' >&2; end
function rpm; echo '4.fc43.nginx1.30.50'; end
function sudo; return 0; end
nginx_dav_ext_is_current
""")
        self.assertNotEqual(result.returncode, 0)

    def test_mismatched_headers_stop_before_writing_spec(self):
        result = self.fish("""
function nginx; echo 'nginx version: nginx/1.30.5' >&2; end
function rpm; echo '1.30.4'; end
function step_warn; echo $argv; end
function sudo; echo 'UNEXPECTED WRITE'; return 0; end
write_nginx_dav_ext_spec /unused/spec
""")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not match", result.stdout)
        self.assertNotIn("UNEXPECTED WRITE", result.stdout)
