#!/usr/bin/env fish
set HV /home/io/.local/bin/hyprvoice
set FLAG /tmp/hyprvoice_music_paused

set hv_status ( $HV status 2>/dev/null )
if test $hv_status
    if string match -q '*status=idle*' -- $hv_status
        if test (playerctl status 2>/dev/null) = Playing
            playerctl pause
            touch $FLAG
        end

        $HV toggle

        if test -f $FLAG
            function __hyprvoice_resume --argument-names hv flag
                for _ in (seq 1 50)
                    set hv_status ( $hv status 2>/dev/null )
                    if not string match -q '*status=idle*' -- $hv_status
                        break
                    end
                    sleep 0.1
                end

                while true
                    set hv_status ( $hv status 2>/dev/null )
                    if string match -q '*status=idle*' -- $hv_status
                        break
                    end
                    sleep 0.2
                end

                playerctl play
                rm -f $flag
            end

            __hyprvoice_resume $HV $FLAG &
            functions -e __hyprvoice_resume
        end
    else
        $HV toggle
        if test -f $FLAG
            playerctl play
            rm -f $FLAG
        end
    end
else
    $HV toggle
end
