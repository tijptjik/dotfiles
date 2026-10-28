-- Reuse native rule matching for initial widths and monitor arrivals.
local widths = {}
local policies, monitors, subscriptions = {}, {}, nil
local pending

function widths.rule(rule)
    local handle = hl.window_rule(rule)
    if rule.scrolling_width then
        local tag = "arrival-width-" .. (#policies + 1)
        local match = {}
        for key, value in pairs(rule.match) do match[key] = value end
        -- Native dynamic tags can lag behind a workspace move. Match the class
        -- natively, but read the destination output directly at arrival.
        local monitor = match.workspace and match.workspace:match("^m%[(.-)%]$")
        if monitor then match.workspace = nil end
        policies[#policies + 1] = { tag = tag, width = rule.scrolling_width, monitor = monitor }
        hl.window_rule({ name = tag, match = match, tag = "+" .. tag })
    end
    return handle
end

local function desired(window)
    local tags = {}
    for _, tag in ipairs(window.tags or {}) do tags[tag:gsub("%*$", "")] = true end
    for i = #policies, 1, -1 do
        local policy = policies[i]
        if tags[policy.tag] and (not policy.monitor or policy.monitor == window.monitor.name) then
            return policy.width
        end
    end
end

local function normal(window)
    return window.mapped and not window.floating and window.workspace
        and window.workspace.id > 0 and window.monitor
end

function widths.refresh()
    -- Move events fire before the compositor finishes attaching the new layout.
    -- The next event-loop turn sees the final monitor, column and matching rules.
    hl.exec_scheduled_prop_refresh_immediately()
    for _, window in ipairs(hl.get_windows()) do
        if normal(window) then
            local address, monitor = window.address, window.monitor.name
            local previous = monitors[address]
            monitors[address] = monitor
            local layout = window.layout
            if previous and previous ~= monitor and layout and layout.name == "scrolling"
                and layout.column and window.fullscreen == 0 and window.fullscreen_client == 0 then
                local width = desired(window)
                if width and math.abs(layout.column.width - width) > 0.001 then
                    local active = hl.get_active_window()
                    if window == active then
                        require("scrolling_gaps").resize(width)
                    else
                        -- colresize targets the focused column. Borrow focus only
                        -- inside this event-loop turn, then restore the view and
                        -- pointer before a frame can render. Pixel resize clamps
                        -- lone/offscreen columns and cannot set an exact fraction.
                        local focused_monitor = hl.get_active_monitor()
                        local focused_workspace = focused_monitor.active_workspace
                        local destination_workspace = window.monitor.active_workspace
                        local cursor = hl.get_cursor_pos()
                        local ok, err = pcall(function()
                            hl.dispatch(hl.dsp.focus({ window = window }))
                            require("scrolling_gaps").resize(width)
                        end)
                        if destination_workspace and destination_workspace.id ~= window.workspace.id then
                            hl.dispatch(hl.dsp.focus({ workspace = destination_workspace.id }))
                        end
                        if active and active.mapped then
                            hl.dispatch(hl.dsp.focus({ window = active }))
                        elseif focused_workspace then
                            hl.dispatch(hl.dsp.focus({ workspace = focused_workspace.id }))
                        else
                            hl.dispatch(hl.dsp.focus({ monitor = focused_monitor.name }))
                        end
                        hl.dispatch(hl.dsp.cursor.move(cursor))
                        if not ok then error(err) end
                    end
                end
            end
        end
    end
    require("scrolling_gaps").update()
end

local function schedule()
    if pending then return end
    pending = hl.timer(function()
        pending = nil
        widths.refresh()
    end, { timeout = 1, type = "oneshot" })
end

function widths.start()
    if subscriptions then return end
    for _, window in ipairs(hl.get_windows()) do
        if normal(window) then monitors[window.address] = window.monitor.name end
    end
    subscriptions = {
        hl.on("window.open", function(window)
            if normal(window) then monitors[window.address] = window.monitor.name end
        end),
        hl.on("window.close", function(window) monitors[window.address] = nil end),
        hl.on("window.move_to_workspace", schedule),
        hl.on("workspace.move_to_monitor", schedule),
    }
end

return widths
