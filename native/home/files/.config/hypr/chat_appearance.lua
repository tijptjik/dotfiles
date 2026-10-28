-- Quiet the desktop behind special workspaces without dimming their windows.
hl.config({ decoration = { dim_special = 0.65 } })

-- Soft theme-background/off-white treatment for unfocused chat side panes.
-- The plugin build has an ABI guard and must be rebuilt after Hyprland upgrades.
local home = os.getenv("HOME")
local plugin = home .. "/.local/lib/hypr/HyprWindowShade.so"
local binary = io.open(plugin, "rb")
if binary then
    binary:close()
    hl.plugin.load(plugin)
    local shader = home .. "/.config/hypr/shaders/chat-blur-dim.glsl"
    -- Replace-mode gives each transition the original full-colour texture,
    -- rather than stacking it on an already monochrome intermediate image.
    for _, entry in ipairs({
        { "inactive", "shader_inactive:" .. shader },
        { "focus", "shader_focus:" .. shader },
        { "unfocus", "shader_unfocus:" .. shader },
        { "replace", "shader_replace:1" },
    }) do
        hl.window_rule({
            name = "chat-appearance-" .. entry[1],
            match = {
                class = "^(com.rtosta.zapzap|org.signal.Signal)$",
                workspace = "special:chat",
            },
            -- Bare tags are removed correctly when workspace matching stops.
            tag = entry[2],
        })
    end
end
