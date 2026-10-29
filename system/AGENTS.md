# Repository guidelines

Preface final summary responses with `# SUMMARY rN`, incrementing N.

Dotjik owns declarative home/system policy for Tjikup. Native manifests and
MiniJinja `.j2` templates are authoritative. Ordinary home files live in
`native/home/files/`, credentials in `native/home/templates/`, system files in
`system/native/HOST/`, and tasks in `native/tasks/`. Shared helpers are in
`native/helpers/`. Do not reintroduce a second deployment engine or interpreter
based fleet orchestration. Generic native behavior belongs in TjikOS Tjikup;
backup/restore behavior belongs in Synctjik.

Run `bash scripts/validate.sh` from the relevant root. Tests may use Python;
production fleet commands must use native Tjikup/Synctjik. Test synthetic homes,
fixtures and mock services; never use live credentials, /etc or Git remotes.
Render templates for Fi, Li and Si separately. `TJIKUP_BINARY` selects the
runner under test. State explicitly whether live behavior was validated.

Preserve unrelated staged, unstaged and untracked work. Do not commit or push
without authorization. Keep credentials/private captures out of Git. Preserve
private-file modes, ownership conditions, receipts, backup gates and locks.
Never interrupt or replace a pinned archive worker. Use the server bootstrap
and rebuild guides before provisioning; do not blanket-apply during recovery.
