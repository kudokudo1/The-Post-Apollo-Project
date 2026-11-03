#!/usr/bin/env bash
# TASKS M13l // read-only source preflight, then separately requested
# disposable native Quickshell -> Node -> private Secret Service acceptance.
# No production QML reload, live TASKS data, current session keyring, or
# persistent workstation config writes. --run creates ONLY test temp state.
set -euo pipefail
umask 077

mode="${1:---preflight}"
if [[ "$#" -gt 2 ]]; then printf 'M13L_REFUSED_ARGUMENTS\n'; exit 2; fi
case "$mode" in
    --preflight|--run|--inside-private-test) ;;
    *) printf 'M13L_REFUSED_ARGUMENTS\n'; exit 2 ;;
esac
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
root="${2:-$(cd -- "$script_dir/../../.." && pwd -P)}"
if [[ ! -d "$root" || ! -d "$root/services/hub" ]]; then
    printf 'M13L_REFUSED_SOURCE_ROOT\n'
    exit 2
fi
module="$root/services/hub/qmldir"
qml="$root/services/hub/TaskEncryptedDraftHostBridgeM13k.qml"
scene="$root/TaskEncryptedDraftAutoHarnessM13l.qml"
host="$root/tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs"
fixture="$root/tests/tasks/fixtures/TaskSecretServiceRoundTripM13g.cjs"
cipher="$root/tests/tasks/fixtures/TaskEncryptedRecoveryM13f.cjs"

for item in "$module" "$qml" "$scene" "$host" "$fixture" "$cipher"; do
    if [[ ! -f "$item" || -L "$item" ]]; then
        printf 'M13L_REFUSED_MISSING_OR_SYMLINK_SOURCE\n'
        exit 2
    fi
done
if ! awk '$0 == "module qs.services.hub" {n++} END {exit n!=1}' "$module"; then
    printf 'M13L_REFUSED_MODULE_ID\n'
    exit 2
fi
if ! awk '$0 == "TaskEncryptedDraftHostBridgeM13k 1.0 TaskEncryptedDraftHostBridgeM13k.qml" {n++} END {exit n!=1}' "$module"; then
    printf 'M13L_REFUSED_MODULE_TYPE\n'
    exit 2
fi
if ! command -v git >/dev/null 2>&1; then
    printf 'M13L_REFUSED_HASH_TOOL\n'
    exit 2
fi
# Pin executable fixture files, including the M13l auto harness.
# Hashes are the reviewed GitHub blobs, not a trust guarantee for plugins
# or for executable files outside this narrow test boundary.
if [[ "$(git hash-object -- "$qml")" != "2f678121aec04f763b0e130f937fec6af0ad2734" ||
      "$(git hash-object -- "$scene")" != "a96e04e03c11283ca2816e3020a073cb273ac3da" ||
      "$(git hash-object -- "$host")" != "40f96104ab48a56267bf4c6aab78bbb4d2a5b41c" ||
      "$(git hash-object -- "$fixture")" != "fe9707077db3e49c6d65edc9c01f9bb6ae2926df" ||
      "$(git hash-object -- "$cipher")" != "ede2a14684c15255244781d8897934472fd7fc2e" ]]; then
    printf 'M13L_REFUSED_UNREVIEWED_SOURCE\n'
    exit 2
fi
printf 'M13L_REVIEWED_SOURCE_READY\n'
if [[ "$mode" == "--preflight" ]]; then
    exit 0
fi

for tool in dbus-run-session gnome-keyring-daemon secret-tool node timeout mktemp; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'M13L_REFUSED_REQUIRED_TOOL\n'
        exit 2
    fi
done
if command -v quickshell >/dev/null 2>&1; then
    shell_binary=quickshell
elif command -v qs >/dev/null 2>&1; then
    shell_binary=qs
else
    printf 'M13L_REFUSED_QUICKSHELL_MISSING\n'
    exit 2
fi

if [[ "$mode" == "--run" ]]; then
    # D-Bus creates a fresh ephemeral bus; the original login bus is not
    # passed on to the child. No global service installation/unlock.
    printf 'M13L_STARTING_PRIVATE_NATIVE_TEST\n'
    M13L_PRIVATE_DRIVER=1 dbus-run-session -- \
        bash "$script_dir/task_m13l_native_ipc.sh" --inside-private-test "$root"
    exit $?
fi

# Even --inside-private-test cannot run on the real user's session bus.
if [[ "${M13L_PRIVATE_DRIVER:-}" != "1" ||
      ! "${DBUS_SESSION_BUS_ADDRESS:-}" =~ ^unix:path=/tmp/dbus-[A-Za-z0-9_-]+(,.*)?$ ||
      "$(id -u)" == "0" ]]; then
    printf 'M13L_REFUSED_NONPRIVATE_BUS\n'
    exit 2
fi

private_home="$(mktemp -d /tmp/postapollo-m13g-m13k-XXXXXXXX)"
if [[ ! -d "$private_home" || -L "$private_home" ||
      "$(stat -c '%a' "$private_home")" != "700" ]]; then
    printf 'M13L_REFUSED_PRIVATE_HOME\n'
    exit 2
fi
# This is the only recursive cleanup target, and it was newly created above.
trap 'rm -rf -- "$private_home"' EXIT

export HOME="$private_home"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export POST_APOLLO_M13G_DISPOSABLE=1
export POST_APOLLO_M13K_ISOLATED=1
mkdir -m 700 -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" \
    "$XDG_CACHE_HOME" "$HOME/m13g-disposable"

# Fake password belongs ONLY to the keyring in this fresh private HOME/bus.
printf '%s' 'M13l-disposable-test-only' |
    gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1

# Check that this really is the new bus, not the login session.
if [[ ! "$DBUS_SESSION_BUS_ADDRESS" =~ ^unix:path=/tmp/dbus-[A-Za-z0-9_-]+(,.*)?$ ]]; then
    printf 'M13L_REFUSED_BUS_CHANGED\n'
    exit 2
fi

# A private log stays under the newly created temp HOME and is cleaned up.
# Only one fixed success marker is accepted, never arbitrary QML output.
log="$private_home/m13l-native.log"
set +e
timeout --signal=TERM --kill-after=3s 60s \
    "$shell_binary" -p "$scene" >"$log" 2>&1
native_code=$?
set -e
if [[ "$native_code" == "0" ]] &&
   awk 'index($0,"M13L_NATIVE_QML_IPC_PASS") { found=1 }
        END { exit !found }' "$log" &&
   [[ ! -e "$HOME/m13g-disposable/draft.enc" ]] &&
   ! secret-tool lookup service post-apollo-m13g-ci id M13gSynthetic001 >/dev/null 2>&1; then
    printf 'M13L_NATIVE_QML_IPC_AND_CLEANUP_PASS\n'
else
    printf 'M13L_NATIVE_TEST_NOT_VERIFIED\n'
    # Report fixed parser/error categories, not raw local logs or secrets.
    if awk 'index($0,"is not a type") {found=1} END {exit !found}' "$log"; then
        printf 'M13L_QML_TYPE_RESOLUTION_FAILURE\n'
    elif [[ "$native_code" == "124" || "$native_code" == "137" ]]; then
        printf 'M13L_NATIVE_TIMEOUT\n'
    else
        printf 'M13L_NATIVE_HOST_OR_QML_REFUSED\n'
    fi
    exit 1
fi
