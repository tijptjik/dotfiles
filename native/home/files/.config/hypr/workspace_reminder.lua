-- A bare Super hold is observed without consuming keys or changing bindings.
local reminder = {}
local subscription, timer, workspace_subscription, special_subscription
local down = {}
local eligible, shown, navigated = false, false, false
local function send(visible)
    if shown == visible then return end
    shown = visible
    hl.dispatch(hl.dsp.exec_cmd('$HOME/.local/bin/bartjikctl ' ..
        (visible and 'show-workspaces' or 'hide-workspaces')))
end
local function cancel()
    eligible = false
    if timer then timer:set_enabled(false); timer = nil end
    navigated = false
    send(false)
end
local function settle()
    if timer then timer:set_enabled(false) end
    -- Workspace transitions use speed 4 (400 ms); keep the result visible
    -- through that transition before Bartjik starts its own fade.
    timer = hl.timer(function()
        timer = nil
        cancel()
    end, { timeout = 400, type = 'oneshot' })
end
local function interaction()
    if shown then navigated = true else cancel() end
end
local function workspace_changed()
    if not shown then return end
    navigated = true
    if not down[133] and not down[134] then settle() end
end
function reminder.key(code, _, state)
    local pressed = state == 1
    if pressed and down[code] then return end -- repeats cannot restart the hold
    if pressed then down[code] = true else down[code] = nil end
    if code ~= 133 and code ~= 134 then
        if pressed then interaction() end
        return
    end
    if not pressed then
        if shown and navigated then settle() else cancel() end
        return
    end
    cancel()
    for key in pairs(down) do
        if key ~= code then return end
    end
    eligible = true
    timer = hl.timer(function()
        timer = nil
        if eligible and down[code] then send(true) end
    end, { timeout = 400, type = 'oneshot' })
end
function reminder.start()
    if subscription then return end
    subscription = hl.on('input.keyboard.key', reminder.key)
    workspace_subscription = hl.on('workspace.active', workspace_changed)
    special_subscription = hl.on('workspace.special_active', workspace_changed)
    for _, key in ipairs({'mouse:272', 'mouse:273', 'mouse:274', 'mouse:275',
                          'mouse:276', 'mouse_up', 'mouse_down', 'mouse_left', 'mouse_right'}) do
        hl.bind(key, interaction, { non_consuming = true, ignore_mods = true,
                              transparent = true, submap_universal = true })
    end
    -- Clear a preview left by a configuration reload.
    hl.dispatch(hl.dsp.exec_cmd('$HOME/.local/bin/bartjikctl hide-workspaces'))
end
return reminder
