#!/bin/sh
# Pin the supported runtime without changing Si's system Node default.
exec /usr/bin/node-22 /opt/codex-vpn/bin/codex "$@"
