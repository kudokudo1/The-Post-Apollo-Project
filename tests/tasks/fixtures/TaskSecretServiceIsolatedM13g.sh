#!/usr/bin/env bash
# M13g: isolated CI session ONLY. No host or user keyring.
set -euo pipefail
umask 077
T="$(mktemp -d /tmp/postapollo-m13g-XXXXXXXX)"
trap 'rm -rf -- "$T"' EXIT
export HOME="$T/home"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export POST_APOLLO_M13G_DISPOSABLE=1
mkdir -m 700 -p "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$HOME/m13g-disposable"
# Create and unlock a throwaway login keyring INSIDE the isolated
# D-Bus session and private HOME. CI-only synthetic password.
printf '%s' 'M13g-CI-throwaway-unlock-only' |
  gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1
probe="$(python3 tests/tasks/fixtures/TaskSecretServiceProbeM13g.py)"
python3 -c 'import json,sys
v=json.loads(sys.argv[1])
assert v["status"]=="SERVICE_ACQUIRED", "isolated Secret Service not acquired"
assert v["authenticated_unlock_verified"] is False
assert v["production_key_provider_selected"] is False' "$probe"
# Two different Node processes, same isolated real Secret Service.
create="$(node tests/tasks/fixtures/TaskSecretServiceRoundTripM13g.cjs create)"
test "$create" = "SYNTHETIC_SECRET_STORED_AND_ENCRYPTED"
reopen="$(node tests/tasks/fixtures/TaskSecretServiceRoundTripM13g.cjs reopen)"
test "$reopen" = "SYNTHETIC_SECRET_SERVICE_RESTART_PASS"
missing="$(node tests/tasks/fixtures/TaskSecretServiceRoundTripM13g.cjs reopen-missing-key)"
test "$missing" = "REFUSED_KEY_NOT_AVAILABLE"
# Clear only the synthetic item in this disposable D-Bus session.
secret-tool clear service post-apollo-m13g-ci id M13gSynthetic001 >/dev/null 2>&1
absent="$(node tests/tasks/fixtures/TaskSecretServiceRoundTripM13g.cjs reopen)"
test "$absent" = "REFUSED_KEY_NOT_AVAILABLE"
printf '%s\n' "M13G_ISOLATED_SECRET_SERVICE_PASS"
