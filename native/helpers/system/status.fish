function __stage_use_color
    isatty stdout; or test "$TJIKUP_COLOR" = 1
end

function __stage_use_spinner
    isatty stdout; and test "$TJIKUP_NO_SPIN" != 1
end

function __stage_fish_color --argument-names color
    switch "$color"
        case 6; echo cyan
        case 8; echo brblack
        case 9; echo brred
        case 10; echo brgreen
        case 11; echo bryellow
        case 12; echo brblue
        case 13; echo brmagenta
        case 14; echo brcyan
        case 15; echo brwhite
        case '*'; echo "$color"
    end
end

function __stage_style --argument-names color text
    set_color (__stage_fish_color "$color")
    printf "%s" "$text"
    set_color normal
end

function __stage_style_bold --argument-names color text
    set_color --bold (__stage_fish_color "$color")
    printf "%s" "$text"
    set_color normal
end

function __stage_color --argument-names verb icon
    if contains -- "$icon" '✗' X; or contains -- "$verb" FAILED ERROR
        echo 9
    else if test "$icon" = '!'; or test "$verb" = WARN
        echo 11
    else if test "$verb" = SKIP; or test "$icon" = '-'
        echo 8
    else if test "$icon" = '✓'
        echo 10
    else
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

    # Tjikup runs Dotjik through sudo.  On FUSE-backed home directories an
    # elevated process can pass `test -w` but still be denied when opening the
    # user-owned tempfile.  Let tee handle the best-effort append so Fish does
    # not print a redirection warning if that happens.
    printf '%s\t%s\t%s\t%s\n' "$stage_name" "$icon" "$subject" "$note" | command tee -a "$TJIKUP_REPORT_FILE" >/dev/null 2>&1
end

function __stage_icon_color --argument-names icon
    switch "$icon"
        case '✓'
            echo 10
        case '!'
            echo 11
        case '✗' X
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
        __stage_style 15 "Tailscale operator for"
        printf " "
        __stage_style 6 "$tailscale_operator[2]"
        return
    end

    # Do not use a capture group here: Fish emits captures as additional values
    # and those values make printf repeat the formatted subject.
    set -l qualifier (string match -r '\[[^]]+\]$|\([^)]*\)$' -- "$subject")
    if test (count $qualifier) -gt 0
        set -l base (string replace -- "$qualifier" "" "$subject" | string trim)
        set -l styled_base (__stage_style 15 "$base")
        set -l styled_qualifier (__stage_style 8 "$qualifier")
        printf "%s %s\n" "$styled_base" "$styled_qualifier"
    else
        __stage_style 15 "$subject"
    end
end

# Public presentation API.  All setup sections use this rather than printing
# headings or spacing themselves, so adjacent scripts compose predictably.
function section_header --argument-names title
    if test "$TJIKUP_NO_SECTIONS" = 1
        return 0
    end
    set -l color 12
    if test (count $argv) -gt 1
        set color $argv[2]
    end
    echo
    if command -q gum; and __stage_use_color
        __stage_style_bold "$color" "$title"
    else
        echo "$title"
    end
    echo
end

# A repository banner leaves one visual line before the title; the following
# section header supplies the single separator after the URL.
function repo_header --argument-names title url
    echo
    if command -q gum; and __stage_use_color
        __stage_style_bold 13 "$title"
        __stage_style 8 "$url"
    else
        echo "$title"
        echo "$url"
    end
end

function output_gap
    echo
end

function __stage_print_row --argument-names icon row
    if isatty stdout; or test "$TJIKUP_COLOR" = 1
        if set -q __stage_pending_row
            printf '\r\033[2K'
            set -e __stage_pending_row
        end
        if test "$icon" = "..."
            printf '%s' "$row"
            set -g __stage_pending_row 1
            return
        end
    end
    printf '%s\n' "$row"
end

function __stage_clear_pending
    if set -q __stage_pending_row
        if isatty stdout; or test "$TJIKUP_COLOR" = 1
            printf '\r\033[2K'
        end
        set -e __stage_pending_row
    end
end

function __stage_label
    set -l row (__stage_render_label $argv)
    __stage_print_row "$argv[2]" "$row"
end

function __stage_label_note
    set -l row (__stage_render_label_note $argv)
    __stage_print_row "$argv[2]" "$row"
end

# Parent tjikup supplies geometry when stdout is piped through run_stream.
function __stage_columns
    if string match -qr '^[0-9]+$' -- "$TJIKUP_COLUMNS"; and test "$TJIKUP_COLUMNS" -ge 24
        echo $TJIKUP_COLUMNS
    else if set -q COLUMNS; and test "$COLUMNS" -ge 24
        echo $COLUMNS
    else
        echo 80
    end
end

function __stage_render_label --argument-names stage_name icon subject
    __stage_event "$stage_name" "$icon" "$subject" ""
    set subject (string shorten --max (math (__stage_columns) - 1 - 9 - (string length --visible -- "$icon")) -- "$subject")
    set -l color (__stage_color "$stage_name" "$icon")
    set -l padded_stage (printf "%-7s" "$stage_name")

    if command -v gum >/dev/null 2>&1; and __stage_use_color
        set -l styled_stage (__stage_style_bold $color "$padded_stage")
        set -l styled_icon (__stage_style "$color" "$icon")
        printf "%s %s " "$styled_stage" "$styled_icon"
        __stage_styled_subject "$subject"
    else
        echo "$padded_stage $icon $subject"
    end
end

function __stage_render_label_note --argument-names stage_name icon subject note
    if test "$icon" = '✓'; and string match -qri '(^|; *)no (changes|updates)$' -- "$note"
        set stage_name SKIP
    end
    __stage_event "$stage_name" "$icon" "$subject" "$note"
    set -l color (__stage_color "$stage_name" "$icon")
    set -l padded_stage (printf "%-7s" "$stage_name")
    set -l available (math (__stage_columns) - 1 - (string length --visible -- "$padded_stage $icon "))
    set note (string shorten --max (math "floor(($available - 2) / 2)") -- "$note")
    set subject (string shorten --max (math "$available - "(string length --visible -- "$note")" - 2") -- "$subject")
    set -l padding (math "$available - "(string length --visible -- "$subject")" - "(string length --visible -- "$note"))
    if test $padding -lt 2
        set padding 2
    end

    if command -v gum >/dev/null 2>&1; and __stage_use_color
        set -l styled_stage (__stage_style_bold $color "$padded_stage")
        set -l styled_icon (__stage_style "$color" "$icon")
        set -l styled_subject (__stage_styled_subject "$subject")
        set -l styled_note (__stage_style 8 "$note")
        printf "%s %s %s%s%s\n" "$styled_stage" "$styled_icon" "$styled_subject" (string repeat -n $padding " ") "$styled_note"
    else
        printf "%s %s %s%s%s\n" "$padded_stage" "$icon" "$subject" (string repeat -n $padding " ") "$note"
    end
end

# Public status-row API. Colours follow the outcome; the optional legacy
# fifth argument is accepted for compatibility.
function status_msg
    set -l stage_name $argv[1]
    set -l icon $argv[2]
    set -l subject $argv[3]

    if test (count $argv) -ge 4
        set -l note $argv[4]
        if test "$icon" = "✓"; and contains -- "$note" "no changes" "no updates"
            __stage_label_note SKIP "$icon" "$subject" "$note"
        else if test (count $argv) -ge 5
            __stage_label_note "$stage_name" "$icon" "$subject" "$note" "$argv[5]"
        else
            __stage_label_note "$stage_name" "$icon" "$subject" "$note"
        end
    else
        __stage_label "$stage_name" "$icon" "$subject"
    end
end

function __stage_spin_title --argument-names stage_name subject
    set subject (string shorten --max (math (__stage_columns) - 13) -- "$subject")
    set -l color (__stage_color "$stage_name" "...")
    set -l padded_stage (printf "%-7s" "$stage_name")

    if command -v gum >/dev/null 2>&1; and __stage_use_color
        set -l styled_stage (__stage_style_bold $color "$padded_stage")
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

    if command -v gum >/dev/null 2>&1; and __stage_use_spinner
        gum spin --spinner dot --title (__stage_spin_title "$stage_name" "$subject") -- bash -c 'while kill -0 "$1" 2>/dev/null; do sleep 0.2; done' bash $pid
    else
        __stage_label "$stage_name" "..." "$subject"
    end

    wait $pid 2>/dev/null
    set -l code (command cat $status_file)

    if test "$code" -eq 0
        if test "$note" = "__silent_success__"
            set -l result (command grep -E '^TJIKUP_RESULT=(changed|unchanged)$' "$log_file" | command tail -n 1)
            switch "$result"
                case TJIKUP_RESULT=unchanged
                    __stage_label_note SKIP "✓" "$subject" "no changes"
                case TJIKUP_RESULT=changed
                    __stage_result "$stage_name" "$subject"
                case '*'
                    __stage_clear_pending
            end
        else if test "$note" = "__silent_failure__"; or string match -q -r '^__silent_failure__:' -- "$note"
            __stage_clear_pending
        else if test -n "$note"
            if contains -- "$note" "no changes" "no updates"
                status_msg "$stage_name" "✓" "$subject" "$note"
            else
                __stage_label_note "$stage_name" "✓" "$subject" "$note" "$stage_name"
            end
        else
            __stage_result "$stage_name" "$subject"
        end
    else
        __stage_failure "$title"
        if string match -q -r '^__silent_failure__:' -- "$note"
            set -l failure_log (string replace -r '^__silent_failure__:' '' -- "$note")
            mkdir -p (dirname "$failure_log")
            and command mv "$log_file" "$failure_log"
        else if test "$note" != "__silent_failure__"
            command cat $log_file
        end
        rm -f $log_file $status_file
        return $code
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
