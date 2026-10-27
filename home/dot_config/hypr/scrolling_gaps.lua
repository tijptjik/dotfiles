-- Focus-sensitive gaps for ordinary tiled scrolling columns. Never fullscreen.
local scrolling_gaps = {}
local subscriptions
local pending
local rules = {}
local enabled = {}

function scrolling_gaps.update()
    local window = hl.get_active_window()
    -- Scratchpads and floating overlays are outside the scrolling flow. Focus
    -- can briefly be nil while opening them; that must not reflow the strip.
    if not window or not window.mapped or window.floating or not window.workspace
        or window.workspace.id <= 0 then return end
    local layout = window.layout
    if not layout or layout.name ~= "scrolling" then return end
    local column = layout.column
    local workspace = window.workspace.id
    local gapless = window.fullscreen == 0 and window.fullscreen_client == 0
        and column ~= nil and math.abs(column.width - 1.0) < 0.001
        and #column.windows == 1
    -- Each strip remembers its own mode. Only another tiled window in that
    -- same workspace can change it; other monitors/workspaces are independent.
    if gapless == (enabled[workspace] or false) then return end
    enabled[workspace] = gapless
    if rules[workspace] then
        rules[workspace]:set_enabled(gapless)
    elseif gapless then
        -- Use a distinct selector, preserving the existing ID/monitor rules.
        rules[workspace] = hl.workspace_rule({
            workspace = "r[" .. workspace .. "-" .. workspace .. "] s[false]",
            gaps_in = 0, gaps_out = 0, border_size = 0, no_rounding = true,
        })
    end
end

function scrolling_gaps.start()
    if subscriptions then return end
    local function schedule()
        if pending then return end
        pending = hl.timer(function()
            pending = nil
            scrolling_gaps.update()
        end, { timeout = 20, type = "oneshot" })
    end
    subscriptions = {
        hl.on("window.active", scrolling_gaps.update),
        hl.on("window.open", schedule),
        hl.on("window.close", schedule),
    }
    schedule()
end

-- Prefer native strip navigation while a neighboring column exists, and
-- retain ordinary monitor navigation at the ends of the strip.
function scrolling_gaps.focus(direction)
    local window = hl.get_active_window()
    local layout = window and window.layout
    if layout and layout.name == "scrolling" and layout.column and window.workspace then
        local index = layout.column.index
        for _, candidate in ipairs(hl.get_windows()) do
            local other = candidate.layout
            if candidate.mapped and not candidate.floating and candidate.workspace
                and candidate.workspace.id == window.workspace.id
                and other and other.name == "scrolling" and other.column
                and ((direction == "l" and other.column.index < index)
                    or (direction == "r" and other.column.index > index)) then
                return hl.dispatch(hl.dsp.layout("focus " .. direction))
            end
        end
    end
    return hl.dispatch(hl.dsp.focus({ direction = direction }))
end

return scrolling_gaps
