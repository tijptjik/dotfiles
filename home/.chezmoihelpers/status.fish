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

function __stage_styled_subject --argument-names subject
    set -l tailscale_operator (string match -r '^Tailscale operator for (.+)$' -- "$subject")
    if test (count $tailscale_operator) -gt 1
        gum style --foreground 15 "Tailscale operator for" | tr -d '\n'
        printf " "
        gum style --foreground 6 "$tailscale_operator[2]"
        return
    end

    # Do not use a capture group here: Fish emits captures as additional values
    # and those values make printf repeat the formatted subject.
    set -l qualifier (string match -r '\[[^]]+\]$|\([^)]*\)$' -- "$subject")
    if test (count $qualifier) -gt 0
        set -l base (string replace -- "$qualifier" "" "$subject" | string trim)
        set -l styled_base (gum style --foreground 15 "$base")
        set -l styled_qualifier (gum style --foreground 8 "$qualifier")
        printf "%s %s\n" "$styled_base" "$styled_qualifier"
    else
        gum style --foreground 15 "$subject"
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
    if command -q gum; and isatty stdout
        gum style --foreground "$color" --bold "$title"
    else
        echo "$title"
    end
    echo
end

# A repository banner leaves one visual line before the title; the following
# section header supplies the single separator after the URL.
function repo_header --argument-names title url
    echo
    if command -q gum; and isatty stdout
        gum style --foreground 13 --bold "$title"
        gum style --foreground 8 "$url"
    else
        echo "$title"
        echo "$url"
    end
end

function output_gap
    echo
end

function __systems_go --argument-names message
    if not command -q gum; or not isatty stdout
        echo "$message"
        return 0
    end

    # `set_color` takes a colour name or RGB value, not an ANSI palette index
    # (unlike gum's --foreground). Keep the wave palette explicit so it works
    # consistently across Fish/terminal versions.
    set -l colors FF5F5F FFAF00 5FFF87 5FD7FF 5F87FF D787FF
    set -l message_length (string length -- "$message")
    set -l terminal_columns $COLUMNS
    if not string match -qr '^[0-9]+$' -- "$terminal_columns"
        set terminal_columns (command tput cols 2>/dev/null)
    end
    if string match -qr '^[0-9]+$' -- "$terminal_columns"
        set -l padding (math "max(0, ($terminal_columns - $message_length) / 2)")
        printf "%s" (string repeat -n $padding " ")
    end

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

    if command -v gum >/dev/null 2>&1; and isatty stdout
        set -l styled_stage (gum style --foreground $color --bold "$padded_stage")
        set -l styled_icon (gum style --foreground (__stage_icon_color "$icon") "$icon")
        printf "%s %s " "$styled_stage" "$styled_icon"
        __stage_styled_subject "$subject"
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

    if command -v gum >/dev/null 2>&1; and isatty stdout
        set -l styled_stage (gum style --foreground $color --bold "$padded_stage")
        set -l styled_icon (gum style --foreground (__stage_icon_color "$icon") "$icon")
        set -l styled_subject (__stage_styled_subject "$subject")
        set -l styled_note (gum style --foreground 8 "$note")
        printf "%s %s %s%s%s\n" "$styled_stage" "$styled_icon" "$styled_subject" (string repeat -n $padding " ") "$styled_note"
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
