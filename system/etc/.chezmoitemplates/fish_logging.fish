function setup_logging
    set -g chezetc_log_tag $argv[1]
    set -g chezetc_stage INSTALL

    switch $chezetc_log_tag
        case linux-dnf-update
            set chezetc_stage UPDATE
        case linux-enable-docker linux-enable-sshd
            set chezetc_stage CONFIG
    end

    function _chezetc_system_log
        if command -q systemd-cat
            echo $argv | systemd-cat -t $chezetc_log_tag 2>/dev/null
        end
    end

    function _chezetc_emit
        echo $argv
        _chezetc_system_log $argv
    end

    function step_header
        set title $argv[1]
        section_header "$title"
        _chezetc_system_log "START $title"
    end

    function step_ok
        set title $argv
        status_msg "$chezetc_stage" "✓" "$title"
        _chezetc_system_log "OK $title"
    end

    function step_skip
        set title $argv
        status_msg SKIP "-" "$title"
        _chezetc_system_log "SKIP $title"
    end

    function step_skip_ok
        set title $argv[1]
        if test (count $argv) -gt 1
            set note $argv[2]
            status_msg SKIP "✓" "$title" "$note"
            _chezetc_system_log "SKIP $title ($note)"
        else
            status_msg SKIP "✓" "$title"
            _chezetc_system_log "SKIP $title"
        end
    end

    function step_unchanged
        step_skip_ok "$argv[1]" "no changes"
    end

    function step_not_configured
        step_skip_ok "$argv[1]" "not configured"
    end

    function step_expected
        step_skip_ok "$argv[1]" "$argv[2]"
    end

    function step_check_ok
        set title $argv[1]
        if test (count $argv) -gt 1
            set note $argv[2]
            status_msg CHECK "✓" "$title" "$note"
            _chezetc_system_log "CHECK $title ($note)"
        else
            status_msg CHECK "✓" "$title"
            _chezetc_system_log "CHECK $title"
        end
    end

    function step_skip_enabled
        step_skip_ok "$argv[1]" enabled
    end

    function step_fail
        set title $argv
        status_msg FAILED "✗" "$title"
        _chezetc_system_log "FAIL $title"
    end

    function step_error --argument-names title message
        status_msg ERROR "X" "$title" "$message"
        _chezetc_system_log "ERROR $title: $message"
        return 1
    end

    function step_note
        set message $argv
        _chezetc_emit "NOTE $message"
    end

    function step_run
        set title $argv[1]
        set cmd $argv[2..]

        if test (count $cmd) -eq 0
            step_fail "$title"
            return 1
        end

        _chezetc_system_log "RUN $title: $cmd"
        if command -q gum; and __stage_use_spinner
            gum spin --show-error --title (__stage_spin_title "$chezetc_stage" "$title") -- $cmd
        else
            status_msg "$chezetc_stage" "..." "$title"
            $cmd
        end

        set run_status $status
        if test $run_status -eq 0
            status_msg "$chezetc_stage" "✓" "$title"
        else
            status_msg FAILED "✗" "$title"
        end

        return $run_status
    end

    function step_run_note
        set title $argv[1]
        set note $argv[2]
        set cmd $argv[3..]

        if test (count $cmd) -eq 0
            step_fail "$title"
            return 1
        end

        _chezetc_system_log "RUN $title: $cmd"
        if command -q gum; and __stage_use_spinner
            gum spin --show-error --title (__stage_spin_title "$chezetc_stage" "$title") -- $cmd
        else
            status_msg "$chezetc_stage" "..." "$title"
            $cmd
        end

        set run_status $status
        if test $run_status -eq 0
            status_msg "$chezetc_stage" "✓" "$title" "$note"
            _chezetc_system_log "OK $title ($note)"
        else
            status_msg FAILED "✗" "$title"
        end

        return $run_status
    end

    function step_run_note_as
        set stage_name $argv[1]
        set title $argv[2]
        set note $argv[3]
        set command $argv[4..]
        set previous_stage $chezetc_stage

        set chezetc_stage $stage_name
        step_run_note "$title" "$note" $command
        set run_status $status
        set chezetc_stage $previous_stage
        return $run_status
    end

    function step_run_note_quiet
        set title $argv[1]
        set note $argv[2]
        set cmd $argv[3..]

        if test (count $cmd) -eq 0
            step_fail "$title"
            return 1
        end

        _chezetc_system_log "RUN $title: $cmd"
        __stage_run "$title" "$chezetc_stage" "$title" "$note" $cmd
    end

    function step_run_quiet
        set title $argv[1]
        set cmd $argv[2..]

        if test (count $cmd) -eq 0
            step_fail "$title"
            return 1
        end

        _chezetc_system_log "RUN $title: $cmd"
        __stage_run "$title" "$chezetc_stage" "$title" "__silent_success__" $cmd
    end

    # DNF prints its transaction summary before it begins downloading and
    # installing packages.  Watch the captured output so that the otherwise
    # quiet update stage can describe that pending work while DNF runs.
    function step_report_dnf_transaction_summary --argument-names log_file
        set summary_found 0

        for line in (command cat "$log_file")
            set fields (string match -r --groups-only '^[[:space:]]*(Installing|Upgrading|Replacing|Removing):[[:space:]]*([0-9]+)[[:space:]]+packages[[:space:]]*$' -- "$line")
            if test (count $fields) -ne 2
                continue
            end

            set action $fields[1]
            switch "$action"
                case Installing
                    set action Install
                case Upgrading
                    set action Upgrade
                case Replacing
                    set action Replace
                case Removing
                    set action Remove
            end

            # Keep this distinct from the overall UPDATE stage: these rows
            # describe DNF's planned transaction, rather than completed work.
            # Retain the SYNC verb but use the package-work colour for a
            # non-empty transaction.
            status_msg SYNC "✓" "$action" "$fields[2] pkgs" INSTALL
            _chezetc_system_log "SYNC $action ($fields[2] pkgs)"
            set summary_found 1
        end

        return (math "1 - $summary_found")
    end

    function step_run_dnf_update
        set title $argv[1]
        set cmd $argv[2..]

        if test (count $cmd) -eq 0
            step_fail "$title"
            return 1
        end

        set log_file (mktemp)
        set status_file (mktemp)
        _chezetc_system_log "RUN $title: $cmd"

        begin
            $cmd >$log_file 2>&1
            echo $status >$status_file
        end &
        set pid $last_pid

        # DNF output is captured so that it cannot flood the ordered report,
        # but metadata refreshes can be silent for a while.  Give the caller
        # an immediate durable indication that the command is alive, then
        # repeat it periodically until DNF produces a transaction summary or
        # exits.
        status_msg SYNC "..." "$title" "running"
        set heartbeat_ticks 0

        set summary_reported 0

        # Keep the progress indicator transient. Once DNF writes its summary,
        # gum clears the spinner and the durable transaction rows replace it.
        if command -q gum; and __stage_use_spinner
            gum spin --spinner dot --title (__stage_spin_title SYNC "$title") -- fish -c '
                set log_file $argv[1]
                set pid $argv[2]
                while kill -0 $pid 2>/dev/null
                    if command grep -Eq "^[[:space:]]*(Installing|Upgrading|Replacing|Removing):[[:space:]]*[0-9]+[[:space:]]+packages[[:space:]]*$" "$log_file"
                        exit 0
                    end
                    sleep 0.2
                end
                exit 1
            ' "$log_file" "$pid"

            if step_report_dnf_transaction_summary "$log_file"
                set summary_reported 1
            end
        end

        while kill -0 $pid 2>/dev/null
            set heartbeat_ticks (math "$heartbeat_ticks + 1")
            if test $heartbeat_ticks -ge 75
                status_msg SYNC "..." "$title" "still running"
                set heartbeat_ticks 0
            end

            if test $summary_reported -eq 0
                if step_report_dnf_transaction_summary "$log_file"
                    set summary_reported 1
                end
            end
            sleep 0.2
        end

        wait $pid 2>/dev/null
        set run_status (command cat $status_file)

        # A short transaction can finish between polling intervals.
        if test $summary_reported -eq 0
            step_report_dnf_transaction_summary "$log_file"
            and set summary_reported 1
        end

        if test "$run_status" -ne 0
            step_fail "$title"
            command cat $log_file
        end

        rm -f $log_file $status_file
        return $run_status
    end

    # Keep an expected or optional command failure to one status line, while
    # leaving the caller free to decide whether the failure is fatal.
    function step_run_silent
        set title $argv[1]
        set cmd $argv[2..]

        if test (count $cmd) -eq 0
            step_fail "$title"
            return 1
        end

        _chezetc_system_log "RUN $title: $cmd"
        __stage_run "$title" "$chezetc_stage" "$title" "__silent_failure__" $cmd
    end

    # As step_run_silent, but retain the command output at a caller-selected
    # location for diagnosis without flooding the interactive apply output.
    function step_run_silent_logged
        set title $argv[1]
        set failure_log $argv[2]
        set cmd $argv[3..]

        if test (count $cmd) -eq 0
            step_fail "$title"
            return 1
        end

        _chezetc_system_log "RUN $title: $cmd"
        __stage_run "$title" "$chezetc_stage" "$title" "__silent_failure__:$failure_log" $cmd
    end

    function step_warn
        set title $argv
        status_msg WARN "!" "$title"
        _chezetc_system_log "WARN $title"
    end

    function step_warn_note
        set title $argv[1]
        set note $argv[2]
        status_msg WARN "!" "$title" "$note"
        _chezetc_system_log "WARN $title ($note)"
    end

    function step_log_created
        set path $argv[1]
        status_msg LOG "✓" "$path" created
        _chezetc_system_log "LOG $path (created)"
    end

    function step_result_note
        set title $argv[1]
        set note $argv[2]
        set color_stage $chezetc_stage

        if contains -- "$note" "no changes" "no updates"
            set color_stage SYNC
        end

        status_msg "$chezetc_stage" "✓" "$title" "$note" "$color_stage"
        _chezetc_system_log "OK $title ($note)"
    end

    function step_run_as
        set stage_name $argv[1]
        set title $argv[2]
        set command $argv[3..]
        set previous_stage $chezetc_stage
        set chezetc_stage $stage_name
        step_run "$title" $command
        set run_status $status
        set chezetc_stage $previous_stage
        return $run_status
    end

    function log
        _chezetc_system_log $argv
    end
end
