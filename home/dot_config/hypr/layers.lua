-- Sourced in ~/.config/hypr/hyprland.lua
-- #######################
-- HYPRLAND :: LAYER SURFACES
-- #######################

-- Waybar is a layer-shell client. Fade it when Hyprland maps or unmaps it
-- (for example, on launch or exit). Waybar's SIGUSR visibility actions are
-- client-side and do not trigger this compositor animation.
hl.layer_rule({
    name = "waybar-fade",
    animation = "fade",
    match = { namespace = "^waybar$" },
})
