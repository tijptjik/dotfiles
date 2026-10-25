# Email archives: mailtjik

The email application now lives in the independent **tooltjik** Turborepo at
`/home/io/code/tooltjik`, under `apps/mailtjik/`.

- [Application guide](https://github.com/tijptjik/tooltjik/blob/main/apps/mailtjik/README.md): installation,
  archive preparation, live capture, searching, reading and recovery.
- [VHS demo](https://github.com/tijptjik/tooltjik/blob/main/apps/mailtjik/docs/demo.gif): synthetic mail only.

Run `mailtjik read` or `mailtjik archive`; `mailtjik` opens the mode chooser.
Build and install from that repository with `bun install` and
`bun run install:local`.

## Configuration boundary

Chezmoi still manages `home/dot_config/document-archive-policy.json`, installed
as `~/.config/document-archive-policy.json`. Keep this encryption policy here.
The application settings are private at `~/.config/mailtjik/config.json`.
Credentials, mail, indexes, manifests, captures and restored messages stay
outside both repositories. Archives are encrypted before upload to the regular
Google Drive `private/archives/mail/structured` destination.

Running archive workers use their existing pinned code snapshots and are not
replaced by application installation. Keep original source backups intact.
