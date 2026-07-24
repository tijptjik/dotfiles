-- Sourced in ~/.config/hypr/hyprland.lua
-- #######################
-- HYPRLAND :: VARIABLES
-- #######################

-- Author : Mart van de Ven
-- Contact : https://type.hk

-- See https://wiki.hypr.land/Configuring/Basics/Variables/

local colors = require("colors")

-- #######################
-- GENERAL
-- #######################

-- See https://wiki.hyprland.org/Configuring/Variables/#general

hl.config({
    general = {
        border_size = 4,
        gaps_in = 6,
        gaps_out = { top = 12, right = 12, bottom = 8, left = 12 },
        col = {
            active_border = colors.fx_active,
            inactive_border = colors.fx_inactive,
        },
        layout = "master",
        resize_on_border = true,
        hover_icon_on_border = false,
    },
})

-- #######################
-- DECORATION
-- #######################

-- See https://wiki.hypr.land/Configuring/Variables/#decoration

hl.config({
    decoration = {
        rounding = 12,
        active_opacity = 1,
        inactive_opacity = 1,
        fullscreen_opacity = 1,
    },
})

-- #######################
-- ANIMATIONS
-- #######################

-- See https://wiki.hypr.land/Configuring/Animations/

hl.config({
    animations = {
        enabled = true,
    },
})

hl.curve("myBezier", {
    type = "bezier",
    points = { { 0.05, 0.9 }, { 0.1, 1.05 } },
})

hl.curve("cubicBezier", {
    type = "bezier",
    points = { { 0.22, 1 }, { 0.36, 1 } },
})

hl.animation({ leaf = "windows", enabled = true, speed = 7, bezier = "myBezier" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 3, bezier = "cubicBezier" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 7, bezier = "default", style = "popin 90%" })
hl.animation({ leaf = "border", enabled = true, speed = 10, bezier = "default" })
hl.animation({ leaf = "fade", enabled = true, speed = 7, bezier = "default" })
-- Layer-shell clients, including Waybar, use this fade instead of a slide.
hl.animation({ leaf = "fadeLayersIn", enabled = true, speed = 5, bezier = "cubicBezier" })
hl.animation({ leaf = "fadeLayersOut", enabled = true, speed = 5, bezier = "cubicBezier" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 4, bezier = "cubicBezier" })

-- #######################
-- INPUT
-- #######################

-- See https://wiki.hypr.land/Configuring/Variables/#input

hl.config({
    input = {
        follow_mouse = 2,
        float_switch_override_focus = 2,
        special_fallthrough = true,
        off_window_axis_events = 3,
        kb_options = "caps:swapescape",
    },
})

-- #######################
-- MISC
-- #######################

-- See https://wiki.hypr.land/Configuring/Variables/#misc

hl.config({
    misc = {
        -- Logos
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
        -- Wake up
        mouse_move_enables_dpms = false,
        key_press_enables_dpms = true,
        -- Launchers
        enable_swallow = true,
        swallow_regex = "kitty",
        -- Resize
        animate_manual_resizes = true,
        animate_mouse_windowdragging = true,
        -- Full Screen
        vrr = 2,
        -- Lock Screen
        allow_session_lock_restore = true,
    },
})

-- #######################
-- BINDS
-- #######################

-- See https://wiki.hypr.land/Configuring/Variables/#binds

hl.config({
    binds = {
        scroll_event_delay = 0,
        workspace_back_and_forth = true,
        hide_special_on_workspace_change = true,
        allow_workspace_cycles = true,
        workspace_center_on = 1,
        focus_preferred_method = 1,
    },
})

-- #######################
-- RENDER
-- #######################

-- See https://wiki.hypr.land/Configuring/Variables/#render

hl.config({
    render = {
        cm_auto_hdr = 1,
        direct_scanout = 1,
    },
})

-- #######################
-- CURSOR
-- #######################

-- See https://wiki.hypr.land/Configuring/Variables/#cursor

hl.config({
    cursor = {
        hide_on_key_press = true,
        -- in seconds, after how many seconds of cursor’s inactivity to hide it. Set to 0 for never.in
        inactive_timeout = 10,
        persistent_warps = true,
        warp_on_change_workspace = 1,
        warp_on_toggle_special = 1,
        no_hardware_cursors = 1,
    },
})

-- #######################
-- ECOSYSTEM
-- #######################

-- See https://wiki.hypr.land/Configuring/Variables/#ecosystem

hl.config({
    ecosystem = {
        no_donation_nag = true,
    },
})

-- #######################
-- QUIRKS
-- #######################

-- hl.config({
--     quirks = {
--         -- Do not advertise HDR as preferred to Chromium/Electron clients.
--         -- This prevents them from incorrectly treating the display as HDR.
--         prefer_hdr = 0,
--     },
-- })
