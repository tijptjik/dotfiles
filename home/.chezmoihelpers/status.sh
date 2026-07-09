#!/usr/bin/env bash

__stage_color() {
  case "$1" in
    INSTALL) printf '10' ;;
    SYNC) printf '12' ;;
    CONFIG) printf '14' ;;
    SKIP) printf '8' ;;
    FAILED) printf '9' ;;
    *) printf '15' ;;
  esac
}

__stage_label() {
  local stage="$1"
  local icon="$2"
  local subject="$3"
  local color
  color="$(__stage_color "$stage")"

  if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
    gum style --foreground "$color" --bold "$stage" | tr -d '\n'
    printf ' '
    gum style --foreground 10 "$icon" | tr -d '\n'
    printf ' '
    gum style --foreground 15 "$subject"
  else
    printf '%s %s %s\n' "$stage" "$icon" "$subject"
  fi
}

__stage_spin_title() {
  local stage="$1"
  local subject="$2"
  local color
  color="$(__stage_color "$stage")"

  if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
    {
      gum style --foreground "$color" --bold "$stage" | tr -d '\n'
      printf ' '
      gum style --foreground 15 "$subject" | tr -d '\n'
    }
  else
    printf '%s ... %s' "$stage" "$subject"
  fi
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
    "$@" >"$log_file" 2>&1
    printf '%s\n' "$?" >"$status_file"
  ) &
  pid="$!"

  if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
    gum spin --spinner dot --title "$(__stage_spin_title "$stage_name" "$subject")" -- bash -c \
      'while kill -0 "$1" 2>/dev/null; do sleep 0.2; done' bash "$pid"
  else
    __stage_label "$stage_name" "..." "$subject"
  fi

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
