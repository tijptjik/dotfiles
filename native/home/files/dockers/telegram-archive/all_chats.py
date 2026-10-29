"""Include archived dialogs in every sweep of the pinned Telegram Archive 9.5.0.

Upstream's type-based mode fetches archived dialogs but only processes them when
explicitly allowlisted. Merge them into the normal list, retaining upstream chat
filters, flood handling and pagination. No account or session data lives here.
"""
import runpy


def include_archived(original):
    """Wrap dialog retrieval without changing explicit archived-only queries."""
    async def get_dialogs(self, archived=False):
        dialogs = await original(self, archived=archived)
        if archived:
            return dialogs
        archived_dialogs = await original(self, archived=True)
        unique = {self._get_marked_id(dialog.entity): dialog for dialog in dialogs}
        for dialog in archived_dialogs:
            unique.setdefault(self._get_marked_id(dialog.entity), dialog)
        return list(unique.values())
    return get_dialogs


if __name__ == '__main__':
    from telegram_archive.telegram_backup import TelegramBackup
    TelegramBackup._get_dialogs = include_archived(TelegramBackup._get_dialogs)
    runpy.run_module('telegram_archive', run_name='__main__')
