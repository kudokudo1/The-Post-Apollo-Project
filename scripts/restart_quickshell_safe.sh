#!/usr/bin/env bash
set -euo pipefail

config_path="${1:-${XDG_CONFIG_HOME:-$HOME/.config}/quickshell}"

# This is intentionally SIGKILL rather than an in-process Quickshell reload.
# The live Qt 6.11 shell has repeatedly crashed while destructing
# ShaderEffectSource-backed items. A process boundary avoids that teardown path
# entirely, then starts the replacement with file watching disabled before QML
# is loaded.
pkill -KILL -x quickshell 2>/dev/null || true
sleep 0.15

exec env QS_DISABLE_FILE_WATCHER=1 \
    quickshell --no-duplicate --daemonize --path "$config_path"
