-- Check the running compositor's commit before asking Hyprland to load a .so.
-- Both local plugins embed GIT_COMMIT_HASH through their native ABI guards.
-- Keep those guards: this preflight avoids upgrade banners, while the native
-- check also verifies library ABI versions before any hooks are installed.
local M = {}

function M.load(path)
    local signature = os.getenv("HYPRLAND_INSTANCE_SIGNATURE") or ""
    local commit = signature:match("^([0-9a-f]+)_")
    local binary = io.open(path, "rb")
    if not binary then return false end
    local contents = binary:read("*a")
    binary:close()
    if not commit or #commit ~= 40 or not contents
        or not contents:find(commit .. "\0", 1, true) then
        print("Skipping Hyprland plugin; rebuild for the running compositor: " .. path)
        return false
    end
    -- load registers the plugin for the end of config parsing and returns nil.
    hl.plugin.load(path)
    return true
end

return M
