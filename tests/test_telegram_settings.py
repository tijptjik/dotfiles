from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import struct

sys.path.insert(0, str(Path(__file__).parents[1] / 'home/dot_local/lib'))
from device_archives.telegram import TelegramSettingsError, read_settings, theme_dependencies, theme_recovery, compact_theme, Reader, decrypt_local, read_tdf
from device_archives.core import ArchiveError, scan
from telegram_fixtures import write_fixture


class TelegramThemeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = {'mode': 'device', 'encrypted': True,
                       'include_files': ['settingss'], 'telegram_themes': True}

    def test_only_referenced_theme_is_selected_and_new_keys_are_discovered(self):
        old = write_fixture(self.root)
        for name in ['key_datas', 'D877F783D5D3EF8Cs', 'AAAAAAAAAAAAAAAAs']:
            (self.root / name).write_bytes(b'not a selected theme')
        self.assertTrue(read_settings(self.root)[0]['night_mode'])
        self.assertEqual(set(scan(self.root, self.policy)), {'settingss', old})
        new = write_fixture(self.root, theme_id=0x9876543210)
        self.assertEqual(set(scan(self.root, self.policy)), {'settingss', new})
        self.assertTrue((self.root / old).exists())

    def test_day_mode_is_preserved(self):
        name = write_fixture(self.root, night=False)
        self.assertFalse(read_settings(self.root)[0]['night_mode'])
        self.assertEqual(set(theme_dependencies(self.root)), {'settingss', name})

    def test_missing_referenced_theme_fails_instead_of_silent_light_fallback(self):
        name = write_fixture(self.root)
        (self.root / name).unlink()
        with self.assertRaisesRegex(ArchiveError, 'Missing or unsafe'):
            scan(self.root, self.policy)

    def test_account_encryption_key_cannot_be_used_as_a_theme(self):
        write_fixture(self.root, theme_key=b'account key is different'.ljust(256, b'!'))
        with self.assertRaisesRegex(TelegramSettingsError, 'cannot be decrypted'):
            theme_dependencies(self.root)

    def test_unknown_settings_format_and_corruption_fail_closed(self):
        write_fixture(self.root, extra=struct.pack('>I', 0xDEAD))
        with self.assertRaisesRegex(TelegramSettingsError, 'Unsupported Telegram settings record'):
            theme_dependencies(self.root)
        name = write_fixture(self.root)
        data = bytearray((self.root / name).read_bytes())
        data[20] ^= 1
        (self.root / name).write_bytes(data)
        with self.assertRaisesRegex(TelegramSettingsError, 'checksum'):
            theme_dependencies(self.root)

    def test_symlink_and_oversized_dependencies_are_rejected(self):
        name = write_fixture(self.root)
        (self.root / name).unlink()
        (self.root / name).symlink_to(self.root / 'settingss')
        with self.assertRaisesRegex(TelegramSettingsError, 'unsafe'):
            theme_dependencies(self.root)
        (self.root / name).unlink()
        with (self.root / name).open('wb') as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(TelegramSettingsError, 'limit'):
            theme_dependencies(self.root)

    def test_changes_between_dependency_discovery_and_hashing_are_rejected(self):
        write_fixture(self.root)
        selected = theme_recovery(self.root)
        write_fixture(self.root, night=False, theme_id=0x1212)
        with patch('device_archives.telegram.theme_recovery', return_value=selected):
            with self.assertRaisesRegex(ArchiveError, 'changed during selection'):
                scan(self.root, self.policy)

    def test_theme_selection_is_backup_only_and_encrypted(self):
        write_fixture(self.root)
        for policy in [self.policy | {'mode': 'sync'}, self.policy | {'encrypted': False}]:
            with self.assertRaisesRegex(ArchiveError, 'encrypted allowlisted backup'):
                scan(self.root, policy)

    def test_compaction_removes_only_cache_and_is_stable_when_cache_changes(self):
        name = write_fixture(self.root, cached_background=b'regenerable pixels' * 10000)
        required, compacted = theme_recovery(self.root)
        original = (self.root / name).read_bytes()
        self.assertLess(len(compacted[name]), 1024)
        self.assertEqual((self.root / name).read_bytes(), original)
        write_fixture(self.root, cached_background=b'other pixels' * 10000)
        self.assertEqual(theme_recovery(self.root)[1], compacted)
        # Telegram's decoder accepts the resulting envelope; compaction is idempotent.
        (self.root / name).write_bytes(compacted[name])
        self.assertEqual(theme_recovery(self.root)[1], compacted)
        self.assertTrue(read_settings(self.root)[0]['night_mode'])
