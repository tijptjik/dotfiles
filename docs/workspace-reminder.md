# Workspace reminder

Hold either Super key alone for 400 ms to reveal only Bartjik's configured
workspace modules on their respective monitors. Release Super to fade them out
in 180 ms. Once revealed, the reminder stays visible while navigating with
Super held. After navigation, releasing Super waits 400 ms for the configured
workspace transition before starting the fade; a further workspace-change event
restarts that settling period. Before the reminder appears, a second key, mouse
button, or scroll cancels the gesture until a new Super press. Short taps do nothing. The reminder does not accept pointer input,
reserve space, or change the ordinary bars' visibility.

`home/dot_config/hypr/workspace_reminder.lua` observes Hyprland's keyboard event
hook (XKB keycodes 133/134) and uses a one-shot timer. `bindings.lua` starts it.
Bartjik, maintained in `/home/io/code/tjikos/apps/bartjik`, supplies the
`show-workspaces` and `hide-workspaces` commands and reuses its existing workspace
module rendering in `WorkspaceReminder.qml`. Install that Bartjik version before
applying these bindings. Reloading Hyprland clears an outstanding reminder.

Run `python3 -B -m unittest discover -s tests -p 'test_workspace_reminder.py' -v`
for timing-state, release, key-repeat, and combination cancellation coverage.
