#!/usr/bin/env bash

__stage_fish_helper="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/status.fish"

__stage_color() {
  case "$1" in
    SKIP) printf '8' ;;
    CHECK|WARN) printf '14' ;;
    SYNC) printf '6' ;;
    INSTALL|PULL|REMOVE|CONFIG|COMMIT|PUSH|FAILED) printf '9' ;;
    *) printf '14' ;;
  esac
}

__stage_label() {
  local stage="$1"
  local icon="$2"
  local subject="$3"
  if command -v fish >/dev/null 2>&1 && [ -f "$__stage_fish_helper" ]; then
    if [ "${__stage_pending_row:-0}" = 1 ]; then
      printf '\r\033[2K'
      __stage_pending_row=0
    fi
    if [ "$icon" = '...' ] && { [ -t 1 ] || [ "${TJIKUP_COLOR:-0}" = 1 ]; }; then
      __stage_pending_row=1
    fi
    local -a arguments=("$stage" "$icon" "$subject")
    [ -z "${STAGE_NOTE:-}" ] || arguments+=("$STAGE_NOTE")
    fish --no-config -c 'source $argv[1]; status_msg $argv[2..-1]' -- "$__stage_fish_helper" "${arguments[@]}"
    return
  fi
  local padded_stage
  local color
  color="$(__stage_color "$stage")"
  printf -v padded_stage '%-7s' "$stage"

  # Bootstrap may run before Fish is installed. Keep this fallback free of
  # terminal queries too; plain rows are safe with any stdin arrangement.
  printf '%s %s %s\n' "$padded_stage" "$icon" "$subject"
}

stage() {
  local title="$1"
  local stage_name="$2"
  local subject="$3"
  shift 3

  local log_file status_file pid code
  log_file="$(mktemp)"
  status_file="$(mktemp)"

  (
    # Do not let the caller's `set -e` terminate this subshell before we
    # record the command status.  `stage` needs that status to display the
    # command output and return the original failure code.
    set +e
    "$@" >"$log_file" 2>&1
    code="$?"
    printf '%s\n' "$code" >"$status_file"
  ) &
  pid="$!"

  __stage_label "$stage_name" "..." "$subject"

  wait "$pid" 2>/dev/null || true
  code="$(cat "$status_file")"

  if [ "$code" -eq 0 ]; then
    __stage_label "$stage_name" "✓" "$subject"
  else
    __stage_label "FAILED" "✗" "$title"
    cat "$log_file"
    rm -f "$log_file" "$status_file"
    return "$code"
  fi

  rm -f "$log_file" "$status_file"
}
