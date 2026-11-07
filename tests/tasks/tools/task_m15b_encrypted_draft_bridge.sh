#!/usr/bin/env bash
# TASKS M15b // real Secret Service and encrypted draft restart, CI ONLY.
set -euo pipefail
umask 077
if [[ "$#" -ne 1 || "${1:-}" != "--run" ||
      "${GITHUB_ACTIONS:-}" != "true" ||
      "${POST_APOLLO_M15B_DISPOSABLE_CI:-}" != "1" ||
      "$(id -u)" == "0" ||
      ! "${DBUS_SESSION_BUS_ADDRESS:-}" =~ ^unix:path=/tmp/dbus-[A-Za-z0-9_-]+(,.*)?$ ]]; then
    printf '%s\n' "M15B_PRIVATE_RUN_REFUSED"
    exit 2
fi
for binary in node gdbus gnome-keyring-daemon secret-tool mktemp; do
    command -v "$binary" >/dev/null 2>&1 || {
      printf '%s\n' "M15B_REQUIRED_TOOL_UNAVAILABLE"; exit 2;
    }
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo="$(cd -- "$script_dir/../../.." && pwd -P)"
worker="$repo/tests/tasks/fixtures/TaskEncryptedDraftPrivateBridgeM15b.cjs"
[[ -f "$worker" && ! -L "$worker" ]] || {
    printf '%s\n' "M15B_PRIVATE_WORKER_UNAVAILABLE"; exit 2;
}
test_home="$(mktemp -d /tmp/postapollo-m15b-private-XXXXXXXX)"
test_vault="$(mktemp -d /tmp/postapollo-m13o-disposable-XXXXXXXX)"
cleanup() {
    secret-tool clear service post-apollo-m15b-disposable-ci \
        id M15bFakeDraft001 >/dev/null 2>&1 || :
    # Only newly created mktemp roots are removed.
    rm -rf -- "$test_vault" "$test_home"
}
trap cleanup EXIT
export HOME="$test_home"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CACHE_HOME="$HOME/.cache"
export POST_APOLLO_M15B_PRIVATE_ROOT="$test_vault"
mkdir -p -m 700 "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"
for directory in "$HOME" "$test_vault"; do
    [[ ! -L "$directory" && "$(stat -c '%a' "$directory")" == "700" ]] ||
        { printf '%s\n' "M15B_PRIVATE_PERMISSIONS_REFUSED"; exit 2; }
done
printf '%s' 'M15b-disposable-CI-password-only' |
    gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1
owner=""
owner_ready=0
for attempt in $(seq 1 20); do
    owner="$(gdbus call --session --dest org.freedesktop.DBus \
        --object-path /org/freedesktop/DBus \
        --method org.freedesktop.DBus.NameHasOwner \
        org.freedesktop.secrets 2>/dev/null || true)"
    if [[ "$owner" =~ ^\([[:space:]]*true[[:space:]]*,?[[:space:]]*\)$ ]]; then
        owner_ready=1
        break
    fi
    sleep 0.1
done
if [[ "$owner_ready" != "1" ]]; then
    if [[ -z "$owner" ]]; then
        printf '%s\n' "M15B_PRIVATE_SECRET_SERVICE_QUERY_FAILED"
    elif [[ "$owner" =~ ^\([[:space:]]*false[[:space:]]*,?[[:space:]]*\)$ ]]; then
        printf '%s\n' "M15B_PRIVATE_SECRET_SERVICE_NOT_RUNNING"
    else
        printf '%s\n' "M15B_PRIVATE_SECRET_SERVICE_UNRECOGNIZED"
    fi
    exit 2
fi
verify() {
    local action="$1" expected="$2" observed
    observed="$(node "$worker" "$action")" ||
        { printf '%s\n' "M15B_PRIVATE_SUBPROCESS_REFUSED"; exit 2; }
    [[ "$observed" == "$expected" ]] ||
        { printf '%s\n' "M15B_PRIVATE_STAGE_REFUSED"; exit 2; }
}
verify capture M15B_PRIVATE_ENCRYPTED_CAPTURE_PASS
verify locked M15B_PRIVATE_LOCKED_INDICATOR_PASS
verify preview-missing-key M15B_PRIVATE_MISSING_KEY_REFUSED
verify preview-wrong-key M15B_PRIVATE_WRONG_KEY_REFUSED
verify preview-source-conflict M15B_PRIVATE_SOURCE_CONFLICT_REFUSED
verify preview M15B_PRIVATE_UNLOCKED_PREVIEW_PASS
verify clear M15B_PRIVATE_CIPHERTEXT_CLEAR_PASS
verify absent M15B_PRIVATE_NO_CHECKPOINT_REFUSED
# Exact fake item removal is distinct from encrypted checkpoint deletion.
secret-tool clear service post-apollo-m15b-disposable-ci \
    id M15bFakeDraft001 >/dev/null 2>&1
if secret-tool lookup service post-apollo-m15b-disposable-ci \
    id M15bFakeDraft001 >/dev/null 2>&1; then
    printf '%s\n' "M15B_PRIVATE_CREDENTIAL_CLEANUP_REFUSED"; exit 2
fi
[[ ! -e "$test_vault/checkpoint.json" &&
   ! -e "$test_vault/writer.lock" ]] || {
    printf '%s\n' "M15B_PRIVATE_CHECKPOINT_CLEANUP_REFUSED"; exit 2;
}
printf '%s\n' "M15B_REAL_KEYRING_PRIVATE_CIPHERTEXT_RESTART_PASS"
