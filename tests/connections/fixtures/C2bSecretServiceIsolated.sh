#!/usr/bin/env bash
set -euo pipefail
# C2b CI-only fake NASA key + a real isolated Secret Service.
# Must be launched by dbus-run-session on GitHub Actions; never on operator PC.
if [[ "${GITHUB_ACTIONS:-}" != true || -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
  printf '%s\n' 'REFUSED_C2B_NOT_ISOLATED_ACTIONS'
  exit 2
fi
for command in node secret-tool gdbus gnome-keyring-daemon; do
  command -v "$command" >/dev/null || { echo "REFUSED_C2B_MISSING_TOOL"; exit 2; }
done

umask 077
temp="$(mktemp -d /tmp/postapollo-c2b-ci-XXXXXXXX)"
seeded=0
cleaned=0
nonce="$(node -e "process.stdout.write(require('node:crypto').randomBytes(16).toString('hex'))")"
script="tests/connections/fixtures/C2bFakeBrokerOnly.cjs"
finish() {
  local status=$?
  trap - EXIT
  if [[ "$seeded" == 1 && "$cleaned" != 1 ]]; then
    local result
    result="$(node "$script" --cleanup "$nonce" 2>/dev/null)" || status=1
    if [[ "$result" != C2B_SYNTHETIC_ITEM_CLEARED ]]; then
      echo "C2B_CLEANUP_UNVERIFIED // exact synthetic item only"
      status=1
    fi
  fi
  # Only remove the known unique /tmp test directory created by mktemp.
  case "$temp" in
    /tmp/postapollo-c2b-ci-*) rm -rf -- "$temp" || status=1 ;;
    *) echo "REFUSED_C2B_TEMP_ROOT"; status=1 ;;
  esac
  exit "$status"
}
trap finish EXIT

export HOME="$temp/home"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export POST_APOLLO_C2B_FAKE_ONLY=1
unset POST_APOLLO_FIRMS_MAP_KEY
mkdir -m 700 -p "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
printf 'C2B_DISPOSABLE_ONLY\n' > "$temp/.c2b-private-bus"
chmod 600 "$temp/.c2b-private-bus"

# CI-only unlock; the password and bus are throwaway and never used outside CI.
printf %s 'Post-Apollo-C2b-CI-disposable-not-a-user-password' |
  gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1

owner="$(gdbus call --session --dest org.freedesktop.DBus \
    --object-path /org/freedesktop/DBus \
    --method org.freedesktop.DBus.NameHasOwner org.freedesktop.secrets)"
[[ "$owner" == "(true,)" ]] || {
  echo "REFUSED_C2B_PRIVATE_SECRET_SERVICE_MISSING"; exit 1;
}

seed="$(node "$script" --seed "$nonce")"
[[ "$seed" == C2B_SYNTHETIC_KEY_STORED ]] || {
  echo "REFUSED_C2B_SYNTHETIC_STORE"; exit 1;
}
seeded=1
expected="$(node "$script" --exercise "$nonce")"
[[ "$expected" == C2B_FAKE_NASA_SCOPE_AND_KEYRING_PASS ]] || {
  echo "REFUSED_C2B_FAKE_ACTION"; exit 1;
}

missing_nonce="00000000000000000000000000000000"
[[ "$nonce" != "$missing_nonce" ]] || { echo "REFUSED_C2B_NONCE_COLLISION"; exit 1; }
missing="$(node "$script" --missing "$missing_nonce")"
[[ "$missing" == C2B_MISSING_KEY_REFUSED ]] || {
  echo "REFUSED_C2B_MISSING_CREDENTIAL_GATE"; exit 1;
}

removed="$(node "$script" --cleanup "$nonce")"
[[ "$removed" == C2B_SYNTHETIC_ITEM_CLEARED ]] || {
  echo "REFUSED_C2B_KEYRING_CLEANUP"; exit 1;
}
cleaned=1
after="$(node "$script" --missing "$nonce")"
[[ "$after" == C2B_MISSING_KEY_REFUSED ]] || {
  echo "REFUSED_C2B_AFTER_CLEAR"; exit 1;
}
echo "C2B_PASS // ISOLATED_SECRET_SERVICE_SYNTHETIC_NASA_SCOPE_AND_CLEANUP"
