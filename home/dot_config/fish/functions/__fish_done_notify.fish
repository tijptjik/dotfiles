function __fish_done_notify --argument-names title message exit_status
    set -l urgency normal
    if set -q __done_notification_urgency_level
        set urgency "$__done_notification_urgency_level"
    end
    if test "$exit_status" -ne 0
        set urgency critical
        if set -q __done_notification_urgency_level_failure
            set urgency "$__done_notification_urgency_level_failure"
        end
    end

    # done handles focus, duration, exclusions, and the optional notification bell.
    command notify-send --hint=int:transient:1 --hint=string:desktop-entry:fish \
        --urgency="$urgency" --icon=fish --app-name=fish \
        --expire-time="$__done_notification_duration" -- "$title" "$message"
end
