local helpers = {}
local waybar_auto_hide_timer
local zen_extensions_subscription
local zen_extension_title_subscription
local staged_zen_windows = {}

local function command_output(command)
    local process = io.popen(command .. " 2>/dev/null")
    if process == nil then
        return ""
    end

    local output = process:read("*a")
    process:close()
    return output
end

local function command_succeeds(command)
    local status = os.execute(command)
    return status == true or status == 0
end

local function is_idle(hyprvoice_status)
    return hyprvoice_status:find("status=idle", 1, true) ~= nil
end

local function file_exists(path)
    local file = io.open(path, "r")
    if file == nil then
        return false
    end

    file:close()
    return true
end

-- Toggle a named special workspace on DP-1 without leaving the focused window
-- on another monitor.
function helpers.toggle_special_workspace(name)
    local target_monitor = "DP-1"
    local special_workspace = name or "chat"
    local active_window = hl.get_active_window()
    local focused_monitor = hl.get_active_monitor()

    if focused_monitor ~= nil and focused_monitor.name == target_monitor then
        hl.dispatch(hl.dsp.workspace.toggle_special(special_workspace))
        return
    end

    hl.config({ cursor = { no_warps = true } })
    hl.dispatch(hl.dsp.focus({ monitor = target_monitor }))
    hl.dispatch(hl.dsp.workspace.toggle_special(special_workspace))
    if active_window ~= nil then
        hl.dispatch(hl.dsp.focus({ window = active_window }))
    end
    hl.config({ cursor = { no_warps = false } })
end

-- Toggle the active window's floating state. Zen and kitty windows receive the
-- same monitor-relative size and centering treatment as the previous helper.
function helpers.toggle_float()
    local active_window = hl.get_active_window()
    if active_window == nil then
        return
    end

    if active_window.floating then
        hl.dispatch(hl.dsp.window.float({ action = "unset", window = active_window }))
        return
    end

    local is_sized_window = active_window.class:match("zen") ~= nil or active_window.class:match("kitty") ~= nil
    hl.dispatch(hl.dsp.window.float({ action = "set", window = active_window }))

    if not is_sized_window or active_window.monitor == nil then
        return
    end

    local window_height = math.floor(active_window.monitor.height / 1.33)
    local window_width = math.floor(window_height * 1.66)
    hl.dispatch(hl.dsp.window.resize({ x = window_width, y = window_height, relative = false, window = active_window }))
    hl.dispatch(hl.dsp.window.center({ window = active_window }))
end

-- Tile up to six HYPE.HK Zen Browser windows on the active workspace. These
-- values intentionally retain the fixed desktop canvas from the original helper.
function helpers.layout_zen_hypehk_mobile()
    local window_width = 500
    local window_height = 889
    local spacing = 24
    local max_windows = 6
    local screen_width = 3440
    local screen_height = 1440
    local screen_x = 0
    local screen_y = 0
    local title = "HYPE.HK — Zen Browser"
    local workspace = hl.get_active_workspace()

    if workspace == nil then
        return
    end

    local windows = {}
    for _, window in ipairs(hl.get_workspace_windows(workspace)) do
        if window.title == title then
            windows[#windows + 1] = window
        end
    end

    local window_count = math.min(#windows, max_windows)
    local total_width = window_count * window_width + (window_count - 1) * spacing
    local start_x = screen_x + math.floor((screen_width - total_width) / 2)
    local start_y = screen_y + math.floor((screen_height - window_height) / 2)

    for index = 1, window_count do
        local window = windows[index]
        local x = start_x + (index - 1) * (window_width + spacing)

        hl.dispatch(hl.dsp.window.float({ action = "set", window = window }))
        hl.dispatch(hl.dsp.window.resize({ x = window_width, y = window_height, relative = false, window = window }))
        hl.dispatch(hl.dsp.window.move({ x = x, y = start_y, relative = false, window = window }))
    end
end

-- Pause media while Hyprvoice records, then resume it when recording completes.
function helpers.toggle_hyprvoice()
    local hyprvoice = os.getenv("HOME") .. "/.local/bin/hyprvoice"
    local pause_flag = "/tmp/hyprvoice_music_paused"
    local status = command_output(hyprvoice .. " status")

    if status == "" then
        os.execute(hyprvoice .. " toggle")
        return
    end

    if not is_idle(status) then
        os.execute(hyprvoice .. " toggle")
        if file_exists(pause_flag) then
            os.execute("playerctl play")
            os.remove(pause_flag)
        end
        return
    end

    if command_output("playerctl status"):match("^Playing") ~= nil then
        os.execute("playerctl pause")
        local flag = io.open(pause_flag, "w")
        if flag ~= nil then
            flag:close()
        end
    end

    os.execute(hyprvoice .. " toggle")

    if not file_exists(pause_flag) then
        return
    end

    local polls = 0
    local recording_started = false
    local timer
    timer = hl.timer(function()
        local timer_status = command_output(hyprvoice .. " status")

        if not recording_started then
            polls = polls + 1
            if not is_idle(timer_status) or polls >= 50 then
                recording_started = true
                timer:set_timeout(200)
            end
            return
        end

        if is_idle(timer_status) then
            os.execute("playerctl play")
            os.remove(pause_flag)
            timer:set_enabled(false)
        end
    end, { timeout = 100, type = "repeat" })
end

-- Show and hide Waybar when the pointer reaches or leaves a screen edge.
function helpers.start_waybar_auto_hide(side)
    side = side or "bottom"
    local safe_zone = 68
    local visible = true

    if waybar_auto_hide_timer ~= nil then
        waybar_auto_hide_timer:set_enabled(false)
    end

    waybar_auto_hide_timer = hl.timer(function()
        local cursor = hl.get_cursor_pos()
        local monitor = hl.get_monitor_at_cursor()

        if cursor == nil or monitor == nil or not command_succeeds("pgrep -x waybar >/dev/null") then
            visible = true
            return
        end

        local x = cursor.x - monitor.x
        local y = cursor.y - monitor.y
        local width = monitor.width / monitor.scale
        local height = monitor.height / monitor.scale
        local at_reveal_edge = false
        local in_safe_zone = false

        if side == "top" then
            at_reveal_edge = y <= 2
            in_safe_zone = y <= safe_zone
        elseif side == "bottom" then
            at_reveal_edge = y >= height - 2
            in_safe_zone = y >= height - safe_zone
        elseif side == "left" then
            at_reveal_edge = x <= 2
            in_safe_zone = x <= safe_zone
        elseif side == "right" then
            at_reveal_edge = x >= width - 2
            in_safe_zone = x >= width - safe_zone
        else
            error("waybar_auto_hide: unsupported side '" .. side .. "'")
        end

        if at_reveal_edge and not visible then
            os.execute("pkill -USR2 -x waybar")
            visible = true
        elseif not in_safe_zone and visible then
            os.execute("pkill -USR1 -x waybar")
            visible = false
        end
    end, { timeout = 100, type = "repeat" })

    return waybar_auto_hide_timer
end

-- Stage new Zen windows off-screen until their title identifies them. This prevents
-- extension popups from briefly joining the active layout before they are floated.
function helpers.start_zen_extensions()
    local extensions = {
        { title = "(Bitwarden Password Manager) - Bitwarden", width = 800, height = 800 },
        { title = "(Authenticator) - Authenticator", width = 335, height = 525 },
    }
    local staging_workspace = "special:staging"

    local function staged_window(window)
        if window == nil or window.address == nil then
            return nil
        end

        return staged_zen_windows[window.address]
    end

    local function restore_staged_window(window)
        local staged = staged_window(window)

        if staged == nil then
            return false
        end

        if staged.timer ~= nil then
            staged.timer:set_enabled(false)
        end

        staged_zen_windows[window.address] = nil
        hl.dispatch(hl.dsp.window.move({ workspace = staged.workspace, follow = false, window = window }))
        return true
    end

    local function float_extension(window)
        if window == nil or window.title == nil or window.class ~= "zen" then
            return false
        end

        for _, extension in ipairs(extensions) do
            if window.title:find(extension.title, 1, true) ~= nil then
                restore_staged_window(window)
                local monitor = window.monitor

                if monitor == nil then
                    return true
                end

                local x = math.floor(monitor.x + (monitor.width - extension.width) / 2)
                local y = math.floor(monitor.y + (monitor.height - extension.height) / 2)
                local max_x = monitor.x + monitor.width - extension.width
                local max_y = monitor.y + monitor.height - extension.height

                x = math.max(monitor.x, math.min(x, max_x))
                y = math.max(monitor.y, math.min(y, max_y))

                hl.dispatch(hl.dsp.window.float({ action = "set", window = window }))
                hl.dispatch(hl.dsp.window.resize({ x = extension.width, y = extension.height, relative = false, window = window }))
                hl.dispatch(hl.dsp.window.move({ x = x, y = y, relative = false, window = window }))
                return true
            end
        end

        return false
    end

    zen_extensions_subscription = hl.on("window.open_early", function(window)
        if window == nil or window.class ~= "zen" or window.address == nil then
            return
        end

        local workspace = window.workspace or hl.get_active_workspace()

        if workspace == nil or workspace.name == staging_workspace then
            return
        end

        local staged = { workspace = workspace }
        staged_zen_windows[window.address] = staged
        hl.dispatch(hl.dsp.window.move({ workspace = staging_workspace, follow = false, window = window }))

        local timer
        timer = hl.timer(function()
            restore_staged_window(window)
        end, { timeout = 750, type = "oneshot" })
        if staged_zen_windows[window.address] == staged then
            staged.timer = timer
        else
            timer:set_enabled(false)
        end
    end)

    zen_extension_title_subscription = hl.on("window.title", function(window)
        if float_extension(window) then
            return
        end

        local staged = staged_window(window)

        -- Zen first reports a generic title. Keep it hidden until a meaningful
        -- title arrives, or until the short timer above releases it.
        if staged ~= nil and window.title ~= nil and window.title ~= "" and window.title ~= "Zen Browser" then
            restore_staged_window(window)
        end
    end)

    for _, window in ipairs(hl.get_windows()) do
        float_extension(window)
    end

    return zen_extensions_subscription
end

return helpers
