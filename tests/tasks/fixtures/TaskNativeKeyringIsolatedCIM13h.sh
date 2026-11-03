#!/usr/bin/env bash
# M13h CI-only dry run of the EXACT operator-facing Fedora harness.
# Executed by workflow under dbus-run-session, NOT the user's session.
# The keyring and HOME below belong to a disposable GitHub runner session.
set -euo pipefail
umask 077
T="$(mktemp -d /tmp/postapollo-m13h-ci-XXXXXXXX)"
trap 'rm -rf -- "$T"' EXIT
export HOME="$T/home"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
mkdir -m 700 -p "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
printf '%s' 'M13h-CI-only-unlock-not-user-credential' |
    gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1
got="$(node tests/tasks/fixtures/TaskNativeKeyringRecoveryM13h.cjs --native-disposable-test)"
test "$got" = "M13H_NATIVE_ENCRYPTED_RESTART_PASS"
# The test itself cleared its random Secret Service item and temp file.
printf '%s\n' "M13H_CI_NATIVE_HARNESS_PASS"
