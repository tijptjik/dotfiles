import datetime as dt
import contextlib
import io
import os
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "home/dot_local/lib"))
from device_archives.core import (
    retention_keep,
    Archives,
    ArchiveError,
    merge_entries,
    scan,
    unpack,
    digest,
)


def f(content):
    return {"type": "file", "mode": 0o600, "size": len(content), "sha256": content}


class MergeTests(unittest.TestCase):
    def test_first_sync_unions_and_reviews_conflicts(self):
        result, changes, conflicts = merge_entries(
            {},
            {"local": f("L"), "same": f("x"), "conflict": f("a")},
            {"remote": f("R"), "same": f("x"), "conflict": f("b")},
        )
        self.assertEqual(conflicts, ["conflict"])
        self.assertIn("local", result)
        self.assertIn("remote", result)

    def test_only_proven_remote_deletion_deletes(self):
        result, _, conflicts = merge_entries(
            {"old": f("a")}, {"old": f("a"), "new-local": f("b")}, {}
        )
        self.assertNotIn("old", result)
        self.assertIn("new-local", result)
        self.assertFalse(conflicts)

    def test_edit_delete_conflict(self):
        self.assertEqual(merge_entries({"x": f("a")}, {"x": f("b")}, {})[2], ["x"])
        self.assertEqual(merge_entries({"x": f("a")}, {}, {"x": f("b")})[2], ["x"])

    def test_local_deletion_and_local_edits_survive_unchanged_source(self):
        result, _, conflicts = merge_entries(
            {"x": f("a"), "y": f("a")}, {"y": f("b")}, {"x": f("a"), "y": f("a")}
        )
        self.assertEqual(result, {"y": f("b")})
        self.assertFalse(conflicts)

    def test_master_is_exact(self):
        self.assertEqual(
            merge_entries({}, {"old": f("a")}, {"new": f("b")}, True)[0],
            {"new": f("b")},
        )

    def test_directory_with_local_addition_survives_remote_removal(self):
        directory = {"type": "dir", "mode": 0o700}
        self.assertEqual(
            merge_entries({"d": directory}, {"d": directory, "d/new": f("a")}, {})[0],
            {"d": directory, "d/new": f("a")},
        )

    def test_structural_conflict_is_not_silently_deleted(self):
        directory = {"type": "dir", "mode": 0o700}
        base, local, incoming = (
            {"d": directory},
            {"d": directory, "d/local": f("a")},
            {"d": f("b")},
        )
        self.assertEqual(merge_entries(base, local, incoming)[2], ["d", "d/local"])
        self.assertEqual(
            merge_entries(
                base, local, incoming, resolutions={"d": "local", "d/local": "local"}
            )[0],
            local,
        )
        self.assertEqual(
            merge_entries(
                base, local, incoming, resolutions={"d": "source", "d/local": "source"}
            )[0],
            incoming,
        )


class RetentionTests(unittest.TestCase):
    def test_calendar_year_boundary_and_deduplication(self):
        refs = [
            {"snapshot": str(i), "created_at": date + "T12:00:00+00:00"}
            for i, date in enumerate(
                ["2025-11-30", "2025-12-28", "2025-12-31", "2026-01-01", "2026-01-02"]
            )
        ]
        current = dt.datetime(2026, 1, 2, tzinfo=dt.timezone.utc)
        self.assertEqual(
            retention_keep(refs, "4", "daily-weekly-monthly", current), {"4", "1", "2"}
        )
        self.assertEqual(retention_keep(refs, "4", "latest", current), {"4"})

    def test_empty_tiers_and_old_history_expire(self):
        refs = [{"snapshot": "old", "created_at": "2020-01-01T00:00:00+00:00"}]
        self.assertEqual(retention_keep(refs, "new", "daily-weekly-monthly"), {"new"})


class ArchiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempkey = tempfile.TemporaryDirectory()
        cls.key = Path(cls.tempkey.name) / "key"
        subprocess.run(
            ["age-keygen", "-o", str(cls.key)], check=True, capture_output=True
        )
        cls.recipient = subprocess.check_output(
            ["age-keygen", "-y", str(cls.key)], text=True
        ).strip()

    @classmethod
    def tearDownClass(cls):
        cls.tempkey.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = {
            "version": 2,
            "master": "fi",
            "remote": str(self.root / "remote"),
            "identity": str(self.key),
            "recipient": self.recipient,
            "folders": {
                ".shared": {"mode": "sync"},
                ".master": {"mode": "master", "exclude": ["ignored"]},
                ".device": {"mode": "device"},
                ".codex": {
                    "mode": "master-backup",
                    "include": ["store.db", "encryption.key"],
                    "sqlite": ["store.db"],
                },
            },
        }
        self.fi = Archives(self.config, self.root / "fi", "fi")
        self.li = Archives(self.config, self.root / "li", "li")
        for app in (self.fi, self.li):
            for folder in self.config["folders"]:
                (app.home / folder).mkdir(parents=True)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()

    def tearDown(self):
        self.output.__exit__(None, None, None)
        self.temp.cleanup()

    def write(self, app, folder, name, text):
        p = app.home / folder / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        p.chmod(0o600)

    def prime(self):
        for folder in (".shared", ".master"):
            self.fi.backup(folder)
            path, _ = self.li.plan(folder, "fi")
            self.li.apply(path)

    def test_identical_backup_skips_staging_upload_and_reuses_hashes(self):
        self.write(self.fi, ".shared", "file", "original")
        first = self.fi.backup(".shared")
        with (
            patch(
                "device_archives.core.stage_tree", side_effect=AssertionError("staged")
            ),
            patch(
                "device_archives.core.file_hash", side_effect=AssertionError("rehashed")
            ),
            patch.object(self.fi.store, "put", side_effect=AssertionError("uploaded")),
        ):
            second = self.fi.backup(".shared")
        self.assertTrue(second["skipped"])
        self.assertEqual(first["snapshot"], second["snapshot"])
        self.assertEqual(len(self.fi.store.completed("fi/.shared")), 1)
        forced = self.fi.backup(".shared", force=True)
        self.assertNotEqual(first["snapshot"], forced["snapshot"])

    def test_change_detection_handles_metadata_deletions_and_same_size_edits(self):
        self.write(self.fi, ".shared", "file", "before")
        first = self.fi.backup(".shared")
        path = self.fi.home / ".shared/file"
        old = path.stat()
        path.write_text("after!")
        os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
        second = self.fi.backup(".shared")
        self.assertNotEqual(first["snapshot"], second["snapshot"])
        os.utime(path, None)  # A timestamp-only change must not create a snapshot.
        self.assertTrue(self.fi.backup(".shared")["skipped"])
        path.chmod(0o640)
        self.assertNotIn("skipped", self.fi.backup(".shared"))
        path.unlink()
        self.assertNotIn("skipped", self.fi.backup(".shared"))
        (self.fi.home / ".shared").chmod(0o750)
        self.assertNotIn("skipped", self.fi.backup(".shared"))

    def test_missing_remote_archive_rebuilt_and_failed_upload_retried(self):
        self.write(self.fi, ".shared", "file", "initial")
        first = self.fi.backup(".shared")
        (
            self.root / "remote/fi/.shared" / first["snapshot"] / "tree.tar.zst.age"
        ).unlink()
        self.assertNotIn("skipped", self.fi.backup(".shared"))
        self.write(self.fi, ".shared", "file", "changed")
        with patch.object(self.fi.store, "put", side_effect=OSError("upload failed")):
            with self.assertRaises(OSError):
                self.fi.backup(".shared")
        self.assertNotIn("skipped", self.fi.backup(".shared"))

    def test_sqlite_change_check_reads_committed_wal(self):
        db = sqlite3.connect(self.fi.home / ".shared/db.sqlite")
        try:
            db.execute("pragma journal_mode=WAL")
            db.execute("pragma wal_autocheckpoint=0")
            db.execute("create table data(value text)")
            db.commit()
            self.fi.backup(".shared")
            self.assertTrue(self.fi.backup(".shared")["skipped"])
            db.execute("insert into data values ('WAL-only change')")
            db.commit()
            self.assertNotIn("skipped", self.fi.backup(".shared"))
            self.assertTrue(self.fi.backup(".shared")["skipped"])
        finally:
            db.close()

    def test_unchanged_retention_and_filter_changes(self):
        self.write(self.fi, ".shared", "included", "a")
        self.write(self.fi, ".shared", "ignored", "a")
        self.config["folders"][".shared"]["exclude"] = ["ignored"]
        self.fi.backup(".shared")
        self.config["folders"][".shared"]["retention"] = "latest"
        self.write(self.fi, ".shared", "ignored", "b")
        with patch.object(self.fi, "prune", wraps=self.fi.prune) as prune:
            self.assertTrue(self.fi.backup(".shared")["skipped"])
            prune.assert_called_once()
        self.config["folders"][".shared"]["exclude"] = []
        self.assertNotIn("skipped", self.fi.backup(".shared"))


    def test_device_groups_match_chezmoi_roles(self):
        self.config["device_groups"] = {
            "desktop": ["fi"],
            "laptop": ["li"],
            "server": ["si"],
            "clients": ["fi", "li"],
            "all": ["fi", "li", "si"],
        }
        self.config["folders"][".shared"]["devices"] = ["all"]
        self.config["folders"][".device"]["devices"] = ["clients"]
        self.config["folders"][".codex"]["devices"] = ["desktop"]
        self.assertEqual(
            self.fi.devices(["clients", "fi", "server"]), ["fi", "li", "si"]
        )
        self.assertEqual(self.fi.device("laptop"), "li")
        self.assertEqual(self.fi.devices(["test-host"]), ["test-host"])
        with self.assertRaises(ArchiveError):
            self.fi.device("clients")
        self.assertTrue(self.fi.eligible(".shared", "si"))
        self.assertFalse(self.fi.eligible(".device", "si"))
        self.assertFalse(self.fi.eligible(".codex", "li"))
        server = Archives(self.config, self.root / "si", "si")
        with self.assertRaises(ArchiveError):
            server.backup(".device")
        with self.assertRaises(ArchiveError):
            server.plan(".device", "fi")

    def test_readiness_is_scoped_and_can_be_separate_from_backup(self):
        self.config["device_groups"] = {"clients": ["fi", "li"], "desktop": ["fi"]}
        self.config["folders"][".shared"]["devices"] = ["clients"]
        self.config["folders"][".master"]["devices"] = ["desktop"]
        self.config["initial_sync_required"] = ["li"]
        Archives(self.config, self.root / "si", "si").ready()
        with self.assertRaises(ArchiveError):
            self.li.ready()
        self.fi.backup(".shared")
        path, _ = self.li.plan(".shared", "fi")
        self.li.apply(path)
        self.li.ready()  # Desktop-only master folder must not block li.
        self.config["initial_sync_required"] = []
        self.li.baseline_path(".shared", "fi").unlink()
        self.li.backup(
            ".shared"
        )  # Independent history; sync does not happen implicitly.

    def test_plaintext_and_legacy_encrypted_restore(self):
        self.write(self.fi, ".shared", "config", "fixture")
        old = self.fi.backup(".shared")
        # Older pointer format has no explicit encryption flag.
        path = self.root / "remote/fi/.shared" / old["snapshot"] / "complete.json"
        legacy = json.loads(path.read_text())
        legacy.pop("encrypted")
        path.write_text(json.dumps(legacy))
        self.config["folders"][".shared"]["encrypted"] = False
        new = self.fi.backup(".shared")
        folder = self.root / "remote/fi/.shared" / new["snapshot"]
        self.assertTrue((folder / "manifest.json").exists())
        self.assertFalse((folder / "tree.tar.zst.age").exists())
        self.li.restore(".shared", "fi", self.root / "plain")
        self.li.restore(".shared", "fi", self.root / "encrypted", old["snapshot"])
        self.assertEqual(scan(self.root / "plain"), scan(self.root / "encrypted"))
        self.li.plan(".shared", "fi")

    def test_retention_prunes_only_after_verified_backup(self):
        self.config["folders"][".shared"]["retention"] = "latest"
        old = self.fi.backup(".shared")
        self.write(self.fi, ".shared", "changed", "new content")
        with patch.object(
            self.fi.store, "get", side_effect=ArchiveError("failed readback")
        ):
            with self.assertRaises(ArchiveError):
                self.fi.backup(".shared")
        self.assertEqual(self.fi.store.completed("fi/.shared"), [old["snapshot"]])
        new = self.fi.backup(".shared")
        self.assertEqual(self.fi.store.completed("fi/.shared"), [new["snapshot"]])
        # Corrupt latest must prevent standalone pruning.
        tree = self.root / "remote/fi/.shared" / new["snapshot"] / "tree.tar.zst.age"
        tree.write_bytes(b"corrupt")
        with self.assertRaises(ArchiveError):
            self.fi.prune(".shared", apply=True)
        self.assertEqual(self.fi.store.completed("fi/.shared"), [new["snapshot"]])

    def test_roundtrip_preserves_permissions_and_symlinks(self):
        self.write(self.fi, ".shared", "config", "secret fixture")
        (self.fi.home / ".shared/link").symlink_to("/outside/never-follow")
        ref = self.fi.backup(".shared")
        dest = self.root / "restore"
        self.li.restore(".shared", "fi", dest)
        self.assertEqual(scan(dest), scan(self.fi.home / ".shared"))
        self.assertEqual((dest / "config").stat().st_mode & 0o777, 0o600)
        ciphertext = (
            self.root / "remote/fi/.shared" / ref["snapshot"] / "tree.tar.zst.age"
        ).read_bytes()
        self.assertNotIn(b"secret fixture", ciphertext)

    def test_snapshot_history_and_machine_isolation(self):
        self.prime()
        self.write(self.fi, ".device", "file", "desktop")
        first = self.fi.backup(".device")
        self.write(self.fi, ".device", "file", "desktop2")
        second = self.fi.backup(".device")
        self.write(self.li, ".device", "file", "laptop")
        self.li.backup(".device")
        self.assertNotEqual(first["snapshot"], second["snapshot"])
        self.li.restore(".device", "fi", self.root / "old", first["snapshot"])
        self.assertEqual((self.root / "old/file").read_text(), "desktop")
        diff = self.fi.diff(".device", "fi", "li", "file")
        self.assertIn("-desktop2", diff["text_diff"])
        self.assertIn("+laptop", diff["text_diff"])
        self.assertTrue(
            (
                self.root / "remote/fi/.device" / first["snapshot"] / "complete.json"
            ).exists()
        )

    def test_first_backup_on_laptop_requires_initial_sync(self):
        with self.assertRaisesRegex(ArchiveError, "First backup blocked"):
            self.li.backup(".device")
        self.prime()
        self.li.ready()

    def test_initial_sync_retains_local_only_and_blocks_conflict(self):
        self.write(self.fi, ".shared", "key", "remote")
        self.write(self.li, ".shared", "key", "local")
        self.write(self.li, ".shared", "unique", "keep")
        self.fi.backup(".shared")
        path, plan = self.li.plan(".shared", "fi")
        self.assertEqual(plan["conflicts"], ["key"])
        with self.assertRaisesRegex(ArchiveError, "Review required"):
            self.li.apply(path)
        self.li.apply(path, {"key": "source"})
        self.assertEqual((self.li.home / ".shared/key").read_text(), "remote")
        self.assertEqual((self.li.home / ".shared/unique").read_text(), "keep")
        self.assertIn(
            "last_synced_at",
            json.loads(self.li.baseline_path(".shared", "fi").read_text()),
        )

    def test_subsequent_deletion_and_addition(self):
        self.write(self.fi, ".shared", "old", "a")
        self.prime()
        (self.fi.home / ".shared/old").unlink()
        self.write(self.li, ".shared", "local-new", "b")
        self.fi.backup(".shared")
        path, plan = self.li.plan(".shared", "fi")
        self.li.apply(path)
        self.assertFalse((self.li.home / ".shared/old").exists())
        self.assertTrue((self.li.home / ".shared/local-new").exists())

    def test_stale_plan_rejected(self):
        self.fi.backup(".shared")
        path, _ = self.li.plan(".shared", "fi")
        self.write(self.li, ".shared", "new", "new")
        with self.assertRaisesRegex(ArchiveError, "changed"):
            self.li.apply(path)

    def test_open_writer_blocks_apply(self):
        self.write(self.fi, ".shared", "file", "data")
        self.write(self.li, ".shared", "file", "data")
        self.fi.backup(".shared")
        path, _ = self.li.plan(".shared", "fi")
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys; f=open(sys.argv[1], 'r+'); print('ready', flush=True); sys.stdin.read()",
                str(self.li.home / ".shared/file"),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), "ready")
            with self.assertRaisesRegex(ArchiveError, "Close the app"):
                self.li.apply(path)
        finally:
            child.communicate(timeout=5)

    def test_failed_swap_restores_original_tree(self):
        from device_archives import core

        self.write(self.fi, ".shared", "remote", "data")
        self.write(self.li, ".shared", "local", "keep")
        self.fi.backup(".shared")
        path, _ = self.li.plan(".shared", "fi")
        before = scan(self.li.home / ".shared")
        real_replace = core.os.replace

        def fail_new(source, target):
            if Path(source).name == "new":
                raise OSError("simulated swap failure")
            return real_replace(source, target)

        with patch.object(core.os, "replace", side_effect=fail_new):
            with self.assertRaisesRegex(OSError, "swap failure"):
                self.li.apply(path)
        self.assertEqual(scan(self.li.home / ".shared"), before)
        self.assertFalse(self.li.baseline_path(".shared", "fi").exists())

    def test_changed_source_latest_does_not_change_pinned_plan(self):
        self.write(self.fi, ".shared", "a", "one")
        self.fi.backup(".shared")
        path, _ = self.li.plan(".shared", "fi")
        self.write(self.fi, ".shared", "a", "two")
        self.fi.backup(".shared")
        self.li.apply(path)
        self.assertEqual((self.li.home / ".shared/a").read_text(), "one")

    def test_master_replaces_and_keeps_excluded_files_and_recovery(self):
        self.write(self.fi, ".master", "new", "fi")
        self.write(self.li, ".master", "old", "li")
        self.write(self.li, ".master", "ignored", "local")
        self.fi.backup(".master")
        path, _ = self.li.plan(".master", "fi")
        receipt = self.li.apply(path)
        self.assertFalse((self.li.home / ".master/old").exists())
        self.assertTrue((self.li.home / ".master/ignored").exists())
        self.assertTrue((Path(receipt["recovery"]) / "old").exists())

    def test_sqlite_wal_snapshot_and_master_only(self):
        p = self.fi.home / ".codex/store.db"
        db = sqlite3.connect(p)
        try:
            db.execute("pragma journal_mode=WAL")
            db.execute("create table test(value text)")
            db.execute("insert into test values ('latest WAL data')")
            db.commit()
            self.write(self.fi, ".codex", "encryption.key", "fixture-key")
            self.fi.backup(".codex")
            self.li.restore(".codex", "fi", self.root / "codex-restore")
            with contextlib.closing(
                sqlite3.connect(self.root / "codex-restore/store.db")
            ) as restored:
                self.assertEqual(
                    restored.execute("select * from test").fetchall(),
                    [("latest WAL data",)],
                )
            self.assertFalse((self.root / "codex-restore/store.db-wal").exists())
            with self.assertRaises(ArchiveError):
                self.li.backup(".codex")
            with self.assertRaises(ArchiveError):
                self.li.plan(".codex", "fi")
        finally:
            db.close()

    def test_failed_upload_does_not_publish_success(self):
        with patch.object(self.fi.store, "put", side_effect=OSError("network failure")):
            with self.assertRaises(OSError):
                self.fi.backup(".shared")
        self.assertFalse((self.root / "remote/fi/.shared/latest.json").exists())
        self.assertFalse(
            (self.fi.state / "backups" / (digest(".shared") + ".json")).exists()
        )

    def test_corrupt_readback_does_not_publish_success(self):
        def corrupt(key, path):
            path.write_bytes(b"corrupt")

        with patch.object(self.fi.store, "get", side_effect=corrupt):
            with self.assertRaisesRegex(ArchiveError, "checksum"):
                self.fi.backup(".shared")
        self.assertFalse((self.root / "remote/fi/.shared/latest.json").exists())
        self.assertEqual(self.fi.store.completed("fi/.shared"), [])

    def test_restore_never_overwrites_destination(self):
        with self.assertRaisesRegex(ArchiveError, "must not exist"):
            self.fi.restore(".device", "fi", self.fi.home / ".device")

    def test_archive_path_traversal_rejected(self):
        with self.assertRaises(ArchiveError):
            unpack(self.root / "unused", {"../escape": f("a")}, self.root / "out")

    def test_manifest_delta_records_deletion(self):
        self.write(self.fi, ".shared", "gone", "a")
        first = self.fi.backup(".shared")
        (self.fi.home / ".shared/gone").unlink()
        self.fi.backup(".shared")
        manifest = json.loads(
            (self.fi.state / "manifests" / (digest(".shared") + ".json")).read_text()
        )
        self.assertEqual(manifest["changes"]["removed"], ["gone"])
        self.assertEqual(manifest["previous_snapshot"], first["snapshot"])


if __name__ == "__main__":
    unittest.main()
