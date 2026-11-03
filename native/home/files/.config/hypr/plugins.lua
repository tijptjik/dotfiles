-- Sourced in ~/.config/hypr/hyprland.lua
-- #######################
-- HYPRLAND :: PLUGINS
-- #######################

-- Author : Mart van de Ven
-- Contact : https://type.hk

-- See https://hypr.land/plugins/

-- Fail closed to ordinary gaps if the version-matched plugin is not built.
-- Build with: ~/.local/share/hypr/plugins/scrolling-gaps/build.sh
local gap_plugin = os.getenv("HOME") .. "/.local/lib/hypr/scrolling-gaps-local.so"
require("plugin_loader").load(gap_plugin)

require("chat_appearance")
