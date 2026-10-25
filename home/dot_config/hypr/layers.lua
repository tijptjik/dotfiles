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

hl.layer_rule({
    name = "network-widget-fade",
    -- QML mirrors fadeLayersIn/Out; geometry must follow the pointer immediately.
    no_anim = true,
    match = { namespace = "^network-widget$" },
})

hl.layer_rule({
    name = "bartjik-panel-immediate",
    -- The drag image and dropped card share this surface; a compositor fade
    -- would interrupt their frame-synchronized handoff and pointer tracking.
    no_anim = true,
    match = { namespace = "^bartjik-panel$" },
})

hl.layer_rule({
    name = "notjik-floating-immediate",
    -- Floating cards follow pointer movement without compositor fades.
    no_anim = true,
    match = { namespace = "^notjik-floating$" },
})
