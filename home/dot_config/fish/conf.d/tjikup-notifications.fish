# Tjikup reports its own result. Keep done's defaults and any user exclusions.
set -q __done_exclude; or set -g __done_exclude '^git (?!push|pull|fetch)'
set -l tjikup_pattern '^\s*(command\s+)?(\S*/)?(?:si|li|fi)?tjikup(?:\s|$)'
contains -- "$tjikup_pattern" $__done_exclude; or set -ga __done_exclude "$tjikup_pattern"
