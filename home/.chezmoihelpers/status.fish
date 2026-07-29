function __stage_color --argument-names verb
    switch "$verb"
        case SKIP
            echo 8
        case CHECK WARN
            echo 14
        case COMPLETE
            echo 10
        case UPDATE INSTALL PULL REMOVE IMPORT ADD CONFIG BUILD RELOAD STOP FAILED LOG COMMIT PUSH
            echo 9
        case SYNC
            echo 6
        case '*'
            echo 14
    end
end

function __stage_event --argument-names stage_name icon subject note
    if not set -q TJIKUP_REPORT_FILE; or test -z "$TJIKUP_REPORT_FILE"; or test "$icon" = "..."
        return
    end

    # Reporting is optional.  A report file supplied by a caller can belong to
    # a different user or be mounted read-only; do not let that obscure the
    # actual stage result with a Fish redirection warning.
    if test -e "$TJIKUP_REPORT_FILE"; and not test -w "$TJIKUP_REPORT_FILE"
        return
    end

    # Report collection is best effort.  Use tee so an inaccessible report
    # target cannot produce a Fish redirection warning in stage output.
    printf '%s\t%s\t%s\t%s\n' "$stage_name" "$icon" "$subject" "$note" | command tee -a "$TJIKUP_REPORT_FILE" >/dev/null 2>&1
end

function __stage_icon_color --argument-names icon
    switch "$icon"
        case '✓'
            echo 10
        case '!'
            echo 11
        case '✗'
            echo 9
        case '-'
            echo 8
        case '*'
            echo 14
    end
end

function __stage_fish_color --argument-names color
    switch "$color"
        case 6
            echo cyan
        case 8
            echo brblack
        case 9
            echo brred
        case 10
            echo brgreen
        case 11
            echo bryellow
        case 12
            echo brblue
        case 13
            echo brmagenta
        case 14
            echo brcyan
        case 15
            echo brwhite
        case '*'
            echo "$color"
    end
end

function __stage_styled_subject --argument-names subject
    set -l tailscale_operator (string match -r '^Tailscale operator for (.+)$' -- "$subject")
    if test (count $tailscale_operator) -gt 1
        set_color (__stage_fish_color 15)
        printf "%s" "Tailscale operator for"
        set_color normal
        printf " "
        set_color (__stage_fish_color 6)
        printf "%s" "$tailscale_operator[2]"
        set_color normal
        return
    end

    # Do not use a capture group here: Fish emits captures as additional values
    # and those values make printf repeat the formatted subject.
    set -l qualifier (string match -r '\[[^]]+\]$|\([^)]*\)$' -- "$subject")
    if test (count $qualifier) -gt 0
        set -l base (string replace -- "$qualifier" "" "$subject" | string trim)
        set_color (__stage_fish_color 15)
        printf "%s" "$base"
        set_color normal
        printf " "
        set_color (__stage_fish_color 8)
        printf "%s" "$qualifier"
        set_color normal
    else
        set_color (__stage_fish_color 15)
        printf "%s" "$subject"
        set_color normal
    end
end

# Public presentation API.  All setup sections use this rather than printing
# headings or spacing themselves, so adjacent scripts compose predictably.
function section_header --argument-names title
    set -l color 12
    if test (count $argv) -gt 1
        set color $argv[2]
    end
    echo
    if isatty stdout
        set_color --bold (__stage_fish_color "$color")
        printf "%s\n" "$title"
        set_color normal
    else
        echo "$title"
    end
    echo
end

# A repository banner leaves one visual line before the title; the following
# section header supplies the single separator after the URL.
function repo_header --argument-names title url
    echo
    if isatty stdout
        set_color --bold (__stage_fish_color 13)
        printf "%s\n" "$title"
        set_color normal
        set_color (__stage_fish_color 8)
        printf "%s\n" "$url"
        set_color normal
    else
        echo "$title"
        echo "$url"
    end
end

function output_gap
    echo
end

function __systems_go --argument-names message
    if not isatty stdout
        echo "$message"
        return 0
    end

    # `set_color` takes a colour name or RGB value, not an ANSI palette index
    # (unlike gum's --foreground). Keep the wave palette explicit so it works
    # consistently across Fish/terminal versions.
    set -l colors FF5F5F FFAF00 5FFF87 5FD7FF 5F87FF D787FF
    set -l message_length (string length -- "$message")
    # Stage notes align to column 72, which defines the report width.
    set -l report_width 72
    set -l padding (math "max(0, ($report_width - $message_length) / 2)")
    set -l padding (math "max(0, floor(($report_width - $message_length) / 2))")
    printf "%s" (string repeat -n $padding " ")

    for index in (seq $message_length)
        set -l character (string sub -s $index -l 1 -- "$message")
        if test "$character" = " "
            printf " "
        else
            set -l color_index (math "($index - 1) % 6 + 1")
            set_color --bold $colors[$color_index]
            printf "%s" "$character"
            set_color normal
        end
    end
    echo
end

function __stage_label --argument-names stage_name icon subject
    __stage_event "$stage_name" "$icon" "$subject" ""
    set -l color (__stage_color "$stage_name")
    set -l padded_stage (printf "%-7s" "$stage_name")

    if isatty stdout
        set_color --bold (__stage_fish_color "$color")
        printf "%s" "$padded_stage"
        set_color normal
        printf " "
        set_color (__stage_fish_color (__stage_icon_color "$icon"))
        printf "%s" "$icon"
        set_color normal
        printf " "
        __stage_styled_subject "$subject"
        printf "\n"
    else
        echo "$padded_stage $icon $subject"
    end
end

function __stage_label_note --argument-names stage_name icon subject note
    __stage_event "$stage_name" "$icon" "$subject" "$note"
    set -l color (__stage_color "$stage_name")
    if test (count $argv) -ge 5
        set color (__stage_color "$argv[5]")
    else if test "$stage_name" = PULL; and test "$note" = "no changes"
        set color 14
    else if test "$stage_name" = SYNC; and contains -- "$note" "no changes" "no updates"
        set color 6
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

    if isatty stdout
        set_color --bold (__stage_fish_color "$color")
        printf "%s" "$padded_stage"
        set_color normal
        printf " "
        set_color (__stage_fish_color (__stage_icon_color "$icon"))
        printf "%s" "$icon"
        set_color normal
        printf " "
        __stage_styled_subject "$subject"
        printf "%s" (string repeat -n $padding " ")
        set_color (__stage_fish_color 8)
        printf "%s\n" "$note"
        set_color normal
    else
        printf "%s %s %s%s%s\n" "$padded_stage" "$icon" "$subject" (string repeat -n $padding " ") "$note"
    end
end

# Public status-row API.  The optional fifth argument selects the display
# colour stage while retaining the recorded stage in reports.
function status_msg
    set -l stage_name $argv[1]
    set -l icon $argv[2]
    set -l subject $argv[3]

    if test (count $argv) -ge 4
        set -l note $argv[4]
        if test (count $argv) -ge 5
            __stage_label_note "$stage_name" "$icon" "$subject" "$note" "$argv[5]"
        else
            __stage_label_note "$stage_name" "$icon" "$subject" "$note"
        end
    else
        __stage_label "$stage_name" "$icon" "$subject"
    end
end

function __stage_spin_title --argument-names stage_name subject
    set -l color (__stage_color "$stage_name")
    set -l padded_stage (printf "%-7s" "$stage_name")

    if isatty stdout
        set_color --bold (__stage_fish_color "$color")
        printf "%s" "$padded_stage"
        set_color normal
        printf " "
        __stage_styled_subject "$subject"
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
        if test "$note" = "__dynamic__"
            set -l note_marker (string match -r '^__stage_note__:.+$' < $log_file | tail -n 1)
            set note (string replace '__stage_note__:' '' -- "$note_marker")
        end

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

function stage_dynamic_note
    __stage_run $argv[1] $argv[2] $argv[3] "__dynamic__" $argv[4..-1]
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
