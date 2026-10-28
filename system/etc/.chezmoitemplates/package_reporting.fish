# Capture only the selected package versions. Package-manager dependencies are
# intentionally absent from these snapshots and therefore from the report.
function snapshot_rpm_versions
    set output_file $argv[1]
    set packages $argv[2..]

    begin
        set seen_packages
        for package in $packages
            if contains -- "$package" $seen_packages
                continue
            end
            set -a seen_packages "$package"

            set versions (rpm -q --qf '%{VERSION}\n' "$package" 2>/dev/null)
            if test $status -eq 0; and test (count $versions) -gt 0
                printf "%s\t%s\n" "$package" "$versions[1]"
            end
        end
    end >$output_file
end

function snapshot_flatpak_versions
    set output_file $argv[1]
    set packages $argv[2..]

    if test (count $packages) -eq 0
        command touch "$output_file"
        return 0
    end

    begin
        for installed in (flatpak list --system --app --columns=application,version 2>/dev/null)
            set fields (string split \t -- "$installed")
            if test (count $fields) -ge 2; and contains -- "$fields[1]" $packages
                printf "%s\t%s\n" "$fields[1]" "$fields[2]"
            end
        end
    end >$output_file
end

function report_package_updates
    set before_file $argv[1]
    set after_file $argv[2]
    set emit_updates 1
    if test (count $argv) -ge 3; and test "$argv[3]" = "--count-only"
        set emit_updates 0
    end

    set -g package_update_count 0

    for updated in (command cat "$after_file")
        set updated_fields (string split \t -- "$updated")
        if test (count $updated_fields) -lt 2
            continue
        end

        set package $updated_fields[1]
        set new_version $updated_fields[2]
        set old_version

        for installed in (command cat "$before_file")
            set installed_fields (string split \t -- "$installed")
            if test (count $installed_fields) -ge 2; and test "$installed_fields[1]" = "$package"
                set old_version $installed_fields[2]
                break
            end
        end

        if test -z "$old_version"
            set -g package_update_count (math "$package_update_count + 1")
            if test $emit_updates -eq 1
                __stage_label_note INSTALL "✓" "$package (new)" "$new_version"
            end
        else if test "$old_version" != "$new_version"
            set -g package_update_count (math "$package_update_count + 1")
            if test $emit_updates -eq 1
                __stage_label_note UPDATE "✓" "$package ($old_version)" "$new_version"
            end
        end
    end
end

function count_package_changes
    set before_file $argv[1]
    set after_file $argv[2]
    set -g package_change_count 0
    set before_entries (command cat "$before_file")
    set after_entries (command cat "$after_file")

    for after in $after_entries
        set after_fields (string split \t -- "$after")
        if test (count $after_fields) -lt 2
            continue
        end

        set old_version
        for before in $before_entries
            set before_fields (string split \t -- "$before")
            if test (count $before_fields) -ge 2; and test "$before_fields[1]" = "$after_fields[1]"
                set old_version $before_fields[2]
                break
            end
        end

        if test -z "$old_version"; or test "$old_version" != "$after_fields[2]"
            set -g package_change_count (math "$package_change_count + 1")
        end
    end

    for before in $before_entries
        set before_fields (string split \t -- "$before")
        if test (count $before_fields) -lt 2
            continue
        end

        set found 0
        for after in $after_entries
            set after_fields (string split \t -- "$after")
            if test (count $after_fields) -ge 2; and test "$after_fields[1]" = "$before_fields[1]"
                set found 1
                break
            end
        end

        if test $found -eq 0
            set -g package_change_count (math "$package_change_count + 1")
        end
    end
end

function snapshot_flatpak_refs
    set output_file $argv[1]
    flatpak list --system --all --columns=ref 2>/dev/null >$output_file
end

function count_removed_entries
    set before_file $argv[1]
    set after_file $argv[2]
    set -g package_change_count 0
    set after_entries (command cat "$after_file")

    for before in (command cat "$before_file")
        if not contains -- "$before" $after_entries
            set -g package_change_count (math "$package_change_count + 1")
        end
    end
end
