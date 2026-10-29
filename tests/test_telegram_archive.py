"""Regression checks for archived-chat coverage in the pinned collector."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'native/home/files/dockers/telegram-archive/all_chats.py'
spec = importlib.util.spec_from_file_location('telegram_all_chats', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AllChatsTests(unittest.IsolatedAsyncioTestCase):
    async def test_merge_retains_normal_and_adds_archived_without_duplicates(self):
        normal = [SimpleNamespace(entity=1), SimpleNamespace(entity=2)]
        archived = [SimpleNamespace(entity=2), SimpleNamespace(entity=3)]
        calls = []

        async def original(client, archived=False):
            calls.append(archived)
            return client.archived if archived else client.normal

        client = SimpleNamespace(normal=normal, archived=archived, _get_marked_id=lambda entity: entity)
        wrapped = module.include_archived(original)
        result = await wrapped(client)
        self.assertEqual([item.entity for item in result], [1, 2, 3])
        self.assertIs(result[1], normal[1])
        self.assertEqual(calls, [False, True])
        calls.clear()
        self.assertIs(await wrapped(client, archived=True), archived)
        self.assertEqual(calls, [True])

    async def test_failed_archive_fetch_does_not_silently_report_partial_scope(self):
        async def original(client, archived=False):
            if archived:
                raise RuntimeError('fetch failed')
            return []
        with self.assertRaisesRegex(RuntimeError, 'fetch failed'):
            await module.include_archived(original)(SimpleNamespace())
