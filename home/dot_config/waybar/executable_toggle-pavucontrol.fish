#!/usr/bin/env fish
if hyprctl clients | grep 'class: org.pulseaudio.pavucontrol' > /dev/null
    flatpak kill org.pulseaudio.pavucontrol
else
    env GTK_THEME=Adwaita:dark flatpak run org.pulseaudio.pavucontrol
end
