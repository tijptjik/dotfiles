-- Expand imv without setting compositor or client fullscreen state.
local gapless = {}
local saved = {}

function gapless.toggle(pid)
    local window
    for _, candidate in ipairs(hl.get_windows()) do
        if candidate.mapped and candidate.class == "imv" and candidate.pid == pid then
            window = candidate
            break
        end
    end
    if not window or window.fullscreen ~= 0 or window.fullscreen_client ~= 0 then return end
    local key = window.address
    local previous = saved[key]
    if previous then
        hl.dispatch(hl.dsp.window.resize({window = window, x = previous.w, y = previous.h, relative = false}))
        hl.dispatch(hl.dsp.window.move({window = window, x = previous.x, y = previous.y, relative = false}))
        if not previous.floating then
            hl.dispatch(hl.dsp.window.float({window = window, action = "unset"}))
        end
        saved[key] = nil
        return
    end
    local monitor = window.monitor
    if not monitor then return end
    saved[key] = {x = window.at.x, y = window.at.y, w = window.size.x,
        h = window.size.y, floating = window.floating}
    if not window.floating then
        hl.dispatch(hl.dsp.window.float({window = window, action = "set"}))
    end
    hl.dispatch(hl.dsp.window.resize({window = window, x = monitor.width / monitor.scale,
        y = monitor.height / monitor.scale, relative = false}))
    hl.dispatch(hl.dsp.window.move({window = window, x = monitor.x, y = monitor.y, relative = false}))
    hl.dispatch(hl.dsp.window.alter_zorder({window = window, mode = "top"}))
end

hl.on("window.close", function(window) saved[window.address] = nil end)
return gapless
