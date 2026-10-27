-- Navigation and sizing only. The scrolling-gaps plugin owns per-window geometry;
-- never change workspace gaps here, since that resizes unrelated columns.
local scrolling_gaps = {}

-- Kept for monitor-arrival callers; native layout mutations already recalculate.
function scrolling_gaps.update() end
-- Compatibility during a scoped apply while an older root config is still loaded.
function scrolling_gaps.start() end

local function strip(window)
    if not window or not window.mapped or window.floating or not window.workspace
        or window.workspace.id <= 0 then return end
    local layout = window.layout
    if not layout or layout.name ~= "scrolling" or not layout.column then return end
    return window.workspace.id, layout.column
end

function scrolling_gaps.resize(width)
    if not strip(hl.get_active_window()) then return end
    return hl.dispatch(hl.dsp.layout("colresize " .. tostring(width)))
end

function scrolling_gaps.focus(direction)
    local workspace, column = strip(hl.get_active_window())
    if workspace then
        for _, candidate in ipairs(hl.get_windows()) do
            local other_workspace, other = strip(candidate)
            if other_workspace == workspace then
                local delta = other.index - column.index
                if (direction == "l" and delta < 0) or (direction == "r" and delta > 0) then
                    return hl.dispatch(hl.dsp.layout("focus " .. direction))
                end
            end
        end
    end
    return hl.dispatch(hl.dsp.focus({ direction = direction }))
end

return scrolling_gaps
