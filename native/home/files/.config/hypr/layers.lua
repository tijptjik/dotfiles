-- Sourced in ~/.config/hypr/hyprland.lua
-- #######################
-- HYPRLAND :: LAYER SURFACES
-- #######################

-- Bartjik bars are layer-shell clients. Fade them when Hyprland maps or unmaps
-- them; its regular hide/show actions remain client-side.
hl.layer_rule({
    name = "bartjik-bar-fade",
    animation = "fade",
    match = { namespace = "^bartjik%-" },
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
