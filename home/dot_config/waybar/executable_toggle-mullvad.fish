#!/usr/bin/env fish
if hyprctl clients | grep 'class: Mullvad VPN' > /dev/null
    killall mullvad-gui
else
    env GTK_THEME=Adwaita:dark /opt/Mullvad\ VPN/mullvad-gui
end
