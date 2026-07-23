function __stage_color --argument-names verb
    switch "$verb"
        case SKIP
            echo 8
        case CHECK WARN
            echo 14
        case INSTALL SYNC PULL REMOVE CONFIG COMMIT PUSH FAILED
            echo 9
        case '*'
            echo 14
    end
end

function __stage_styled_subject --argument-names subject
    set -l qualifier (string match -r '\[[^]]+\]$' -- "$subject")
    if test (count $qualifier) -gt 0
        set -l base (string replace -- "$qualifier" "" "$subject" | string trim)
        set -l styled_base (gum style --foreground 15 "$base")
        set -l styled_qualifier (gum style --foreground 8 "$qualifier")
        printf "%s %s\n" "$styled_base" "$styled_qualifier"
    else
        gum style --foreground 15 "$subject"
    end
end

function __stage_label --argument-names stage_name icon subject
    set -l color (__stage_color "$stage_name")
    set -l padded_stage (printf "%-7s" "$stage_name")

    if command -v gum >/dev/null 2>&1; and isatty stdout
        set -l styled_stage (gum style --foreground $color --bold "$padded_stage")
        set -l styled_icon (gum style --foreground 10 "$icon")
        printf "%s %s " "$styled_stage" "$styled_icon"
        __stage_styled_subject "$subject"
    else
        echo "$padded_stage $icon $subject"
    end
end

function __stage_label_note --argument-names stage_name icon subject note
    set -l color (__stage_color "$stage_name")
    if test "$stage_name" = PULL; and test "$note" = "no changes"
        set color 14
    end
    set -l padded_stage (printf "%-7s" "$stage_name")
    set -l note_column 72
    set -l prefix_length 10
    set -l subject_length (string length -- "$subject")
    set -l note_length (string length -- "$note")
    set -l padding (math "$note_column - $prefix_length - $subject_length - $note_length")
    if test $padding -lt 2
        set padding 2
    end

    if command -v gum >/dev/null 2>&1; and isatty stdout
        set -l styled_stage (gum style --foreground $color --bold "$padded_stage")
        set -l styled_icon (gum style --foreground 10 "$icon")
        set -l styled_subject (__stage_styled_subject "$subject")
        set -l styled_note (gum style --foreground 8 "$note")
        printf "%s %s %s%s%s\n" "$styled_stage" "$styled_icon" "$styled_subject" (string repeat -n $padding " ") "$styled_note"
    else
        printf "%s %s %s%s%s\n" "$padded_stage" "$icon" "$subject" (string repeat -n $padding " ") "$note"
    end
end

function __stage_spin_title --argument-names stage_name subject
    set -l color (__stage_color "$stage_name")
    set -l padded_stage (printf "%-7s" "$stage_name")

    if command -v gum >/dev/null 2>&1; and isatty stdout
        set -l styled_stage (gum style --foreground $color --bold "$padded_stage")
        set -l styled_subject (__stage_styled_subject "$subject")
        printf "%s %s" "$styled_stage" "$styled_subject"
    else
        printf "%s ... %s" "$padded_stage" "$subject"
    end
end

function __stage_result --argument-names stage_name subject
    __stage_label "$stage_name" "✓" "$subject"
end

function __stage_failure --argument-names message
    __stage_label FAILED "✗" "$message"
end

function __stage_run
    set -l title $argv[1]
    set -l stage_name $argv[2]
    set -l subject $argv[3]
    set -l note $argv[4]
    set -l command $argv[5]
    set -l args $argv[6..-1]
    set -l log_file (mktemp)
    set -l status_file (mktemp)

    begin
        $command $args >$log_file 2>&1
        echo $status >$status_file
    end &
    set -l pid $last_pid

    if command -v gum >/dev/null 2>&1; and isatty stdout
        gum spin --spinner dot --title (__stage_spin_title "$stage_name" "$subject") -- bash -c 'while kill -0 "$1" 2>/dev/null; do sleep 0.2; done' bash $pid
    else
        __stage_label "$stage_name" "..." "$subject"
    end

    wait $pid 2>/dev/null
    set -l code (cat $status_file)

    if test "$code" -eq 0
        if test -n "$note"
            __stage_label_note "$stage_name" "✓" "$subject" "$note"
        else
            __stage_result "$stage_name" "$subject"
        end
    else
        __stage_failure "$title"
        cat $log_file
        rm -f $log_file $status_file
        exit $code
    end

    rm -f $log_file $status_file
end

function stage
    __stage_run $argv[1] $argv[2] $argv[3] "" $argv[4..-1]
end

function stage_note
    __stage_run $argv[1] $argv[2] $argv[3] $argv[4] $argv[5..-1]
end

function interactive_stage
    set -l title $argv[1]
    set -l stage_name $argv[2]
    set -l subject $argv[3]
    set -l command $argv[4]
    set -l args $argv[5..-1]

    __stage_label "$stage_name" "..." "$subject"
    $command $args
    set -l code $status

    if test "$code" -eq 0
        __stage_result "$stage_name" "$subject"
    else
        __stage_failure "$title"
        exit $code
    end
end
