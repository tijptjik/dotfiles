import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = (Path(__file__).parents[1] / "home/dot_local/bin/executable_cloudflare-restic-backup")
LOADER = SourceFileLoader("cloudflare_restic_backup", str(SCRIPT))
SPEC = importlib.util.spec_from_loader("cloudflare_restic_backup", LOADER)
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)


class CloudflareResticGuardTests(unittest.TestCase):
    def test_mount_guard_accepts_exact_uuid_at_exact_path(self):
        result = subprocess.CompletedProcess([], 0, stdout=backup.MOUNT_UUID + " rw,nosuid\n")
        with mock.patch.object(backup.os.path, "ismount", return_value=True), \
             mock.patch.object(backup, "run", return_value=result):
            backup.verify_mount()

    def test_mount_guard_rejects_missing_mount(self):
        with mock.patch.object(backup.os.path, "ismount", return_value=False):
            with self.assertRaisesRegex(backup.BackupError, "not mounted"):
                backup.verify_mount()

    def test_mount_guard_rejects_wrong_uuid(self):
        result = subprocess.CompletedProcess([], 0, stdout="OTHER-UUID rw,nosuid\n")
        with mock.patch.object(backup.os.path, "ismount", return_value=True), \
             mock.patch.object(backup, "run", return_value=result):
            with self.assertRaisesRegex(backup.BackupError, "does not match"):
                backup.verify_mount()

    def test_repository_guard_rejects_read_only_mount(self):
        result = subprocess.CompletedProcess([], 0, stdout=backup.MOUNT_UUID + " ro,nosuid\n")
        with mock.patch.object(backup.os.path, "ismount", return_value=True), \
             mock.patch.object(backup, "run", return_value=result):
            with self.assertRaisesRegex(backup.BackupError, "mounted read-only"):
                backup.verify_repository_path()

    def test_mount_guard_rejects_symlinked_mount_path(self):
        with mock.patch("pathlib.Path.is_symlink", return_value=True):
            with self.assertRaisesRegex(backup.BackupError, "not mounted"):
                backup.verify_mount()


class CloudflareResticExportTests(unittest.TestCase):
    def test_page_pagination_collects_all_pages(self):
        with mock.patch.object(backup, "cloudflare_request", side_effect=[
                ([{"id": "one"}, {"id": "two"}], None),
                ([{"id": "three"}], None)]) as request:
            result = backup.paged_results("token", "/zones", query={"per_page": 2})
        self.assertEqual([item["id"] for item in result], ["one", "two", "three"])
        self.assertEqual(request.call_count, 2)

    def test_private_secret_must_not_be_group_or_world_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token"
            path.write_text("do-not-print")
            path.chmod(0o644)
            with self.assertRaisesRegex(backup.BackupError, "owner-only"):
                backup.safe_secret_file(path)

    def test_private_secret_must_not_be_a_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real"
            real.write_text("do-not-print")
            real.chmod(0o600)
            link = Path(tmp) / "token"
            link.symlink_to(real)
            with self.assertRaisesRegex(backup.BackupError, "must not be a symlink"):
                backup.safe_secret_file(link)

    def test_private_secret_is_read_without_printing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token"
            path.write_text("do-not-print")
            path.chmod(0o600)
            self.assertEqual(backup.safe_secret_file(path), "do-not-print")

    def test_r2_inventory_records_bucket_and_object_totals(self):
        buckets = "".join(f"-1 2026-01-01 00:00:00 -1 bucket-{n}\n" for n in range(18))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
                backup, "run", side_effect=[
                    subprocess.CompletedProcess([], 0, stdout='{"count": 38464, "bytes": 20409653480}'),
                    subprocess.CompletedProcess([], 0, stdout=buckets),
                ]):
            result = backup.export_r2_inventory(Path(tmp))
            manifest = __import__("json").loads((Path(tmp) / "r2/inventory.json").read_text())
        self.assertEqual(result, (18, 38464, 20409653480))
        self.assertEqual(len(manifest["buckets"]), 18)

    def test_dry_run_exports_counts_without_touching_restic(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            config = Path(tmp) / "rclone.conf"
            config.write_text("private configuration")
            config.chmod(0o600)
            old_umask = __import__("os").umask(0o077)
            with mock.patch.object(backup, "STATE", state), \
                 mock.patch.object(backup, "RCLONE_CONFIG", config), \
                 mock.patch.object(backup, "verify_repository_path"), \
                 mock.patch.object(backup, "safe_secret_file", return_value="secret"), \
                 mock.patch.object(backup, "export_zones", return_value=(11, 25)), \
                 mock.patch.object(backup, "export_kv", return_value=(2, 1)), \
                 mock.patch.object(backup, "export_r2_inventory", return_value=(18, 38464, 20409653480)), \
                 mock.patch.object(backup, "restic") as restic_call:
                backup.backup(dry_run=True)
            __import__("os").umask(old_umask)
            restic_call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
