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

# A dirty local checkout may have different QML/host behavior. Before
# actually executing it, pin the THREE executable entrypoints to reviewed
# GitHub main blobs. git hash-object READS bytes; it never stages or writes.
if ! command -v git >/dev/null 2>&1; then
    printf 'M13J_GIT_HASH_TOOL_MISSING\n'
    exit 2
fi
if [[ "$(git hash-object -- "$component")" != "069a1be6fa9cc2b77d5e1701debf1b4c8b269ac2" ||
      "$(git hash-object -- "$host")" != "6d49e3e2067b45b8ab243ed70461b4ea61689daf" ||
      "$(git hash-object -- "$panel")" != "46dded5561e4c9b79ee2ef0820f838a9833d838e" ]]; then
    printf 'M13J_SOURCE_NOT_REVIEWED\n'
    exit 2
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
