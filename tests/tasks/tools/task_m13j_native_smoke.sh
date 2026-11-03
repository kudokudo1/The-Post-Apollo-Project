#!/usr/bin/env bash
# TASKS M13j: read-only local M13i QML module preflight + separately launched panel.
# Never checks out, pulls, changes, repairs or restarts the production shell.
# --preflight does not launch a process. --run explicitly launches ONLY
# the standalone read-only panel, not shell.qml or a storage writer.
set -euo pipefail

mode="${1:---preflight}"
if [[ "$#" -gt 2 ]]; then
    printf 'M13J_REFUSED_ARGS\n'
    exit 2
fi
case "$mode" in
    --preflight|--run) ;;
    *) printf 'M13J_REFUSED_ARGS\n'; exit 2 ;;
esac

root="${2:-${XDG_CONFIG_HOME:-$HOME/.config}/quickshell}"
if [[ ! -d "$root" ]]; then
    printf 'M13J_REFUSED_ROOT_MISSING\n'
    exit 2
fi

hub="$root/services/hub"
module="$hub/qmldir"
component="$hub/TaskEncryptedRecoveryBridgeM13i.qml"
host="$hub/TaskRecoveryProviderHostM13i.py"
panel="$root/TaskEncryptedRecoveryHarnessM13i.qml"
for item in "$module" "$component" "$host" "$panel"; do
    if [[ ! -f "$item" ]]; then
        # Only fixed status text, never leak local file paths.
        case "$item" in
            "$module") printf 'M13J_MISSING_QMLDIR\n' ;;
            "$component") printf 'M13J_MISSING_BRIDGE_QML\n' ;;
            "$host") printf 'M13J_MISSING_READONLY_HOST\n' ;;
            "$panel") printf 'M13J_MISSING_STANDALONE_PANEL\n' ;;
        esac
        exit 2
    fi
done

# Do not use grep: user shell may map it to ripgrep.
if ! awk '$0 == "module qs.services.hub" { found=1 } END { exit !found }' "$module"; then
    printf 'M13J_INVALID_HUB_MODULE\n'
    exit 2
fi

entry='TaskEncryptedRecoveryBridgeM13i 1.0 TaskEncryptedRecoveryBridgeM13i.qml'
if ! awk -v expected="$entry" '
    $0 == expected { n++ }
    END { exit !(n==1) }
' "$module"; then
    printf 'M13J_BRIDGE_UNREGISTERED\n'
    exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
    printf 'M13J_PYTHON_MISSING\n'
    exit 2
fi
if ! command -v gdbus >/dev/null 2>&1; then
    printf 'M13J_GDBUS_MISSING\n'
    exit 2
fi
printf 'M13J_LOCAL_MODULE_READY\n'

if [[ "$mode" == "--preflight" ]]; then
    exit 0
fi

# No writes or repair. This starts another, separately scoped Quickshell
# instance; never quits, reloads or signals any running production instance.
if command -v quickshell >/dev/null 2>&1; then
    shell_binary=quickshell
elif command -v qs >/dev/null 2>&1; then
    shell_binary=qs
else
    printf 'M13J_QUICKSHELL_MISSING\n'
    exit 2
fi
printf 'M13J_STARTING_STANDALONE_PANEL\n'
exec "$shell_binary" -p "$panel"
