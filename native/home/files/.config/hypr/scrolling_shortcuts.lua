-- Column operations for the horizontal scrolling layout.
local shortcuts = {}

local function current()
    local window = hl.get_active_window()
    if not window or not window.mapped or window.floating then return end
    local layout = window.layout
    if not layout or layout.name ~= "scrolling" or not layout.column then return end
    return window, layout
end

local function columns(workspace)
    local result = {}
    for _, window in ipairs(hl.get_windows()) do
        if window.mapped and not window.floating and window.workspace
            and window.workspace.id == workspace then
            local layout = window.layout
            if layout and layout.name == "scrolling" and layout.column then
                result[layout.column.index] = true
            end
        end
    end
    local indices = {}
    for index in pairs(result) do indices[#indices + 1] = index end
    table.sort(indices)
    return indices
end

local function place(window, index)
    -- Native swaps keep each column intact and preserve the other columns' order.
    local distance = index - window.layout.column.index
    local direction = distance < 0 and "l" or "r"
    for _ = 1, math.abs(distance) do
        hl.dispatch(hl.dsp.layout("swapcol " .. direction))
    end
end

function shortcuts.move_column(direction)
    local window, layout = current()
    if not window or not window.workspace or window.workspace.id <= 0
        or window.fullscreen ~= 0 then return end
    local indices = columns(window.workspace.id)
    local at_edge = direction == "l" and layout.column.index == indices[1]
        or direction == "r" and layout.column.index == indices[#indices]
    if not at_edge then return hl.dispatch(hl.dsp.layout("swapcol " .. direction)) end

    local monitors = {}
    for _, monitor in ipairs(hl.get_monitors()) do
        if not monitor.is_mirror and monitor.dpms_status and monitor.active_workspace then
            monitors[#monitors + 1] = monitor
        end
    end
    table.sort(monitors, function(a, b)
        if a.x ~= b.x then return a.x < b.x end
        if a.y ~= b.y then return a.y < b.y end
        return a.name < b.name
    end)
    local source
    for i, monitor in ipairs(monitors) do
        if monitor.name == window.monitor.name then source = i end
    end
    if not source then return end
    local step = direction == "l" and -1 or 1
    local destination = monitors[(source - 1 + step) % #monitors + 1]
    if destination.name == window.monitor.name then
        return place(window, direction == "r" and indices[1] or indices[#indices])
    end
    local workspace = destination.active_workspace
    if workspace.tiled_layout ~= "scrolling" then return end
    local members = layout.column.windows
    local anchor
    for _, member in ipairs(members) do
        hl.dispatch(hl.dsp.window.move({window = member, workspace = workspace.id, follow = true}))
        if anchor then
            -- Reassemble a stacked column in its original top-to-bottom order.
            place(member, anchor.layout.column.index + 1)
            hl.dispatch(hl.dsp.layout("consume_or_expel prev"))
        else
            anchor = member
        end
    end
    hl.dispatch(hl.dsp.focus({window = window}))
    local target_indices = columns(workspace.id)
    place(window, direction == "r" and target_indices[1] or target_indices[#target_indices])
    require("scrolling_widths").refresh()
    require("scrolling_gaps").update()
end

function shortcuts.pair(direction)
    local window, layout = current()
    if not window or not window.workspace or window.workspace.id <= 0
        or window.fullscreen ~= 0 or window.fullscreen_client ~= 0 then return end
    local offset = direction == "l" and -1 or 1
    local neighbor
    for _, candidate in ipairs(hl.get_windows()) do
        if candidate.mapped and not candidate.floating and candidate.workspace
            and candidate.workspace.id == window.workspace.id then
            local other = candidate.layout
            if other and other.name == "scrolling" and other.column
                and other.column.index == layout.column.index + offset then
                neighbor = candidate
                break
            end
        end
    end
    if not neighbor or neighbor.fullscreen ~= 0 or neighbor.fullscreen_client ~= 0 then return end

    -- Resize only this pair. Fitting each half in turn aligns the viewport with
    -- their shared outer edges, even when more columns exist on either side.
    local fit_method = hl.get_config("scrolling:focus_fit_method")
    local no_warps = hl.get_config("cursor:no_warps")
    local follow_mouse = hl.get_config("input:follow_mouse")
    -- Borrow focus without warping through intermediate column positions.
    hl.config({ scrolling = { focus_fit_method = 1 }, cursor = { no_warps = true },
        input = { follow_mouse = 0 } })
    local ok, err = pcall(function()
        hl.dispatch(hl.dsp.layout("colresize 0.5"))
        hl.dispatch(hl.dsp.focus({ window = neighbor }))
        hl.dispatch(hl.dsp.layout("colresize 0.5"))
    end)
    hl.dispatch(hl.dsp.focus({ window = window }))
    hl.dispatch(hl.dsp.layout("fit_into_view"))
    -- The old full-width center can become the gap between the two halves.
    -- Move into the final active half, then restore keyboard focus explicitly:
    -- hover hit testing can still see the old geometry during the animation.
    local at, size = window.at, window.size
    hl.dispatch(hl.dsp.cursor.move({ x = at.x + size.x / 2, y = at.y + size.y / 2 }))
    hl.dispatch(hl.dsp.focus({ window = window }))
    hl.config({ scrolling = { focus_fit_method = fit_method }, cursor = { no_warps = no_warps },
        input = { follow_mouse = follow_mouse } })
    if not ok then error(err) end
end

function shortcuts.transfer(direction)
    local window, layout = current()
    if not window then return end
    local offset = direction == "l" and -1 or 1
    for _, candidate in ipairs(hl.get_windows()) do
        if candidate.mapped and not candidate.floating and candidate.workspace
            and candidate.workspace.id == window.workspace.id then
            local other = candidate.layout
            if other and other.name == "scrolling" and other.column
                and other.column.index == layout.column.index + offset then
                -- Native placement uses pointer height in the destination column.
                return hl.dispatch(hl.dsp.window.move({ direction = direction }))
            end
        end
    end
end

function shortcuts.extract(direction)
    local window, layout = current()
    if not window or #layout.column.windows < 2 then return end
    -- Guard the native dual-purpose action: a singleton would be consumed.
    return hl.dispatch(hl.dsp.layout("consume_or_expel " .. (direction == "l" and "prev" or "next")))
end

function shortcuts.reorder(direction)
    local window, layout = current()
    if not window then return end
    local count = #layout.column.windows
    if count < 2 then return end
    local index = layout.index_in_column -- Native layout indices are zero-based.
    local at_edge = (direction == "u" and index == 0)
        or (direction == "d" and index == count - 1)
    if at_edge then
        local opposite = direction == "u" and "d" or "u"
        -- Rotate the active window through the column, preserving sibling order.
        for _ = 1, count - 1 do
            hl.dispatch(hl.dsp.window.move({ direction = opposite }))
        end
    else
        hl.dispatch(hl.dsp.window.move({ direction = direction }))
    end
end

return shortcuts
