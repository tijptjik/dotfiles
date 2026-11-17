local source = assert(arg[1])
local real_open, real_popen, real_execute, real_remove = io.open, io.popen, os.execute, os.remove
local function scenario(players, failed, stop_with_shortcut)
    local state, flag, commands, timers = 'idle', nil, {}, {}
    io.popen = function(command)
        local result
        if command:find('hyprvoice status', 1, true) then result = 'STATUS status=' .. state
        elseif command:find('--list-all', 1, true) then
            local names = {}
            for _, player in ipairs(players) do table.insert(names, player[1]) end
            result = table.concat(names, '\n')
        else
            local name = command:match("%-%-player='([^']+)' status")
            for _, player in ipairs(players) do if name == player[1] then result = player[2] end end
            assert(result, command)
        end
        return {read=function() return result end, close=function() end}
    end
    os.execute = function(command)
        table.insert(commands, command)
        if command:find('hyprvoice toggle', 1, true) then
            state = state == 'idle' and 'recording' or 'idle'
        end
        if failed and command:find("--player='" .. failed .. "' pause", 1, true) then return nil end
        return true
    end
    io.open = function(path, mode)
        assert(path == '/tmp/hyprvoice_music_paused')
        if mode == 'r' and flag == nil then return nil end
        return {close=function() end, write=function(_, text) flag=text end,
            lines=function() return flag:gmatch('[^\n]+') end}
    end
    os.remove = function() flag=nil end
    hl = {timer=function(callback)
        local t = {callback=callback, enabled=true, set_timeout=function() end,
            set_enabled=function(self, enabled) self.enabled=enabled end}
        table.insert(timers, t)
        return t
    end}
    local helpers = dofile(source)
    helpers.toggle_hyprvoice()
    for _, player in ipairs(players) do
        local found = false
        for _, command in ipairs(commands) do
            if command == "playerctl --player='" .. player[1] .. "' pause" then found=true end
        end
        assert(found == (player[2] == 'Playing'), player[1] .. ' pause mismatch')
    end
    if timers[1] then
        timers[1].callback()
        if stop_with_shortcut then helpers.toggle_hyprvoice()
        else state='idle'; timers[1].callback() end
        assert(not timers[1].enabled, 'completion must disable timer')
    end
    for _, player in ipairs(players) do
        local count = 0
        for _, command in ipairs(commands) do
            if command == "playerctl --player='" .. player[1] .. "' play" then count=count+1 end
        end
        local expected = player[2] == 'Playing' and player[1] ~= failed and 1 or 0
        assert(count == expected, player[1] .. ' resume mismatch')
    end
    assert(flag == nil)
end
scenario({{'TelegramDesktop','Paused'},{'spotify','Playing'}})
scenario({{'TelegramDesktop','Paused'},{'spotify','Playing'},{'vlc.instance42','Playing'}}, nil, true)
scenario({{'spotify','Playing'},{'vlc','Playing'}}, 'vlc')
scenario({{'TelegramDesktop','Paused'}})
scenario({})
io.open, io.popen, os.execute, os.remove = real_open, real_popen, real_execute, real_remove
print('PASS: player selection, multiple players, failed pause, empty/paused players, automatic and manual completion')
