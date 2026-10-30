# Tasktjik rollout

Apply the committed TjikOS and Dotjik revisions to Si with `sitjikup` first.
Tasktjik is installed and configured on Si without a graphical dependency or a
reminder timer. Si uses the existing `~/.local/share/runtjik-todo` authority;
no records are moved or copied. Then apply Fi/Li with their normal Tjikup flow.
Clients use strict-host-key SSH through Mullvad exclusion to `m@ssh.type.hk`.
Existing SSH credentials and trust remain external to the repository.

The Tasktjik configuration group owns configuration and client systemd units.
Client activation disables the legacy `runtjik-todo.timer` before enabling
`tasktjik.timer`. Runtjik and Notjik installation/update depend on Tasktjik.
Tasktjik's new configuration overrides the legacy Runtjik Todo settings.
Set the optional vault locally through policy when a specific vault is chosen.

This prepares rollout only: no live host or timer has been changed. Existing
backup policy and archive workers are unchanged; this is not a backup receipt.
Verify Si capabilities and a synthetic task round trip before rolling clients.
The separate browser Read later integration remains disconnected in concurrent
TjikOS work; Tasktjik rollout does not enable that action.

Older pinned Tjikup runners build/install Tasktjik directly; newer runners
advertise `tasktjik_install_cache` and reuse the native install cache. No runner
release or release-pin change is required for this rollout.
