# System policy

Tjikup deploys Fi, Li and Si through `native/HOST/manifest.json`. Ordinary
maintenance uses `/usr/local/lib/tjikup/tjikup system ...` and
`/etc/tjikup/maintenance.json`. Maintenance templates are in the parent
`native/tasks/system/` directory. Synctjik owns backup/restore engines.

Use `systjik plan`, `systjik check` and `systjik apply` for file operations;
`tjikup --apply-sysfiles` also runs selected recipe tasks. Read
[server bootstrap](SERVER-BOOTSTRAP.md) and [rebuild](SERVER-REBUILD.md) before
server recovery. Do not blanket-apply a recovered machine before verifying its
storage identities, credentials and application data.

`bash scripts/validate.sh` validates synthetic policy and template fixtures.
See [the parent workflow guide](../docs/tjikup.md) for public commands and the
current deferred release boundary.
