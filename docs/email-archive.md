# Email archive format

The structured archive is stored under Google Drive `private/archives/mail/structured/`.
Every data object is compressed with zstd and encrypted with age before upload.
Drive filenames use opaque account and mailbox IDs; the encrypted SQLite index
and JSONL manifest map those IDs to addresses and original source paths.

Each canonical account has three encrypted data collections:

- `mailboxes/`: standard MBOX files, one per original mailbox source. Reader
  views retain text and inline images, and replace non-inline MIME attachments
  with a filename, size, and SHA-256 reference.
- `raw-messages.tar.zst.age`: one exact preserved message payload per unique
  raw-message SHA-256, including its original MIME attachments.
- `attachments.tar.zst.age`: non-inline attachment files, deduplicated by
  content SHA-256. Inline images remain in the MBOX view and raw message.

Large MBOX views are split into numbered parts. Each part is a valid MBOX file;
import the parts in order or concatenate the decrypted/decompressed parts when
a single file is preferred. The manifest records the source mailbox and the
part that contains each reader-view message.

The index collection contains the sensitive `manifest.jsonl` and
`email-index.sqlite`. SQLite FTS5 indexes subjects and header addresses, not
bodies. Message-ID is searchable but is not unique. Exact raw-message hashes
drive deduplication; all source and folder memberships remain in the index.
The Gmail All Mail view is named `Gmail Archive` and excludes messages that
also belong to another folder for the same account. Those memberships remain
available in the manifest and index.

The age identity is the managed `~/.keys/chezmoi.txt` key, recoverable from
Bitwarden. The identity was checked against the configured archive recipient.

## Restore and read

Decrypt an MBOX reader view and pipe it to a standard MBOX file:

```sh
age -d -i ~/.keys/chezmoi.txt account-mailbox.part-0001.mbox.zst.age \
  | zstd -d > restored.mbox
```

Import `restored.mbox` into Thunderbird using an MBOX importer, or open it with
another MBOX-compatible mail client. No custom mail interface is required.

Restore the raw messages or attachment collection with:

```sh
age -d -i ~/.keys/chezmoi.txt raw-messages.tar.zst.age \
  | zstd -d | tar -xf -
```

The SQLite index can be opened with `sqlite3` or a graphical SQLite browser.
For example, search the FTS5 subject and header-address index with:

```sql
SELECT m.subject, m.normalized_utc, m.from_header, m.to_header, m.sha256
FROM message_search s
JOIN messages m ON m.rowid = s.rowid
WHERE message_search MATCH 'invoice';
```

Keep the original source archives until the encrypted exports have been
reparsed, their message and attachment hashes have been compared with the
index, and a restore has been tested.
