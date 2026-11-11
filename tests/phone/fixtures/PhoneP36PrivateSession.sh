#!/usr/bin/env bash
# P36 CI only: after dbus-run-session has created its own private bus, this
# script gives that bus a disposable HOME and a disposable GNOME Keyring.
# NEVER run against the operator's actual HOME, keyring or persistent data.
set -euo pipefail
umask 077
test -n "${DBUS_SESSION_BUS_ADDRESS:-}"
T="$(mktemp -d /tmp/postapollo-p36-ci-XXXXXXXX)"
cleanup() {
  rm -rf -- "$T"
}
trap cleanup EXIT
export HOME="$T/home"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export P36_PRIVATE_TEST="P36_DISPOSABLE_PRIVATE_SESSION"
mkdir -m 700 -p "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
# Only the private D-Bus and private HOME are in scope for this unlock.
printf '%s' 'P36 throwaway CI-only passphrase' |
  gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1
result="$(python3 -B tests/phone/fixtures/PhoneP36DisposableKeyring.py)"
test "$result" = "P36_DISPOSABLE_KEYRING_AND_VAULT_PASS"
printf '%s\n' "P36_CI_PRIVATE_SECRET_SERVICE_PASS"
