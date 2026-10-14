#!/usr/bin/env bash
set -euo pipefail

config_path="${1:-${XDG_CONFIG_HOME:-$HOME/.config}/quickshell}"
runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Fail before touching the live desktop when prerequisites are missing.
if [[ ! -f "$config_path/shell.qml" ]]; then
    printf 'Quickshell restart refused: missing shell.qml at %s\n' "$config_path" >&2
    exit 1
fi
for command_name in quickshell pkill pgrep flock; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        printf 'Quickshell restart refused: missing %s\n' "$command_name" >&2
        exit 1
    fi
done
if [[ ! -d "$runtime_dir" || ! -w "$runtime_dir" ]]; then
    printf 'Quickshell restart refused: runtime directory unavailable: %s\n' "$runtime_dir" >&2
    exit 1
fi

# Repeated shortcut presses must not overlap kill/start sequences.
umask 077
exec 9>"$runtime_dir/post-apollo-quickshell-restart.lock"
if ! flock -n 9; then
    printf 'Quickshell restart already in progress; not starting another.\n' >&2
    exit 1
fi

# A process boundary avoids the Qt 6.11 ShaderEffectSource teardown crashes.
# Wait for the old process to disappear before invoking --no-duplicate;
# an arbitrary 150ms sleep could race with Quickshell's instance cleanup.
pkill -KILL -x quickshell 2>/dev/null || true
stopped=false
for ((attempt = 0; attempt < 50; ++attempt)); do
    if ! pgrep -x quickshell >/dev/null 2>&1; then
        stopped=true
        break
    fi
    sleep 0.1
done
if [[ "$stopped" != true ]]; then
    printf 'Quickshell restart stopped: old process still present after 5s.\n' >&2
    exit 1
fi

# Allow the instance registration to retire after the process exits.
sleep 0.25

# The caller's POST_APOLLO_* diagnostic flags are intentionally inherited.
# Preserve disabled file watching to avoid in-process shader teardown.
if env QS_DISABLE_FILE_WATCHER=1 \
    quickshell --no-duplicate --daemonize --path "$config_path"; then
    flock -u 9
else
    code=$?
    printf 'Quickshell launch returned exit status %s.\n' "$code" >&2
    flock -u 9
    exit "$code"
fi
