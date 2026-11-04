#!/usr/bin/env bash
# M13k CI only: actual GNOME Keyring under a freshly-created private bus/HOME.
# Called ONLY by GitHub workflow inside dbus-run-session.
set -euo pipefail
umask 077
T="$(mktemp -d /tmp/postapollo-m13g-m13k-XXXXXXXX)"
trap 'rm -rf -- "$T"' EXIT
export HOME="$T"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
export POST_APOLLO_M13G_DISPOSABLE=1
export POST_APOLLO_M13K_ISOLATED=1
mkdir -m 700 -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$HOME/m13g-disposable"
printf '%s' 'M13k-fake-CI-only-not-user-credential' |
  gnome-keyring-daemon --unlock --components=secrets >/dev/null 2>&1
request='{"protocol":1,"kind":"RUN_SYNTHETIC_DRAFT","consent":"CI_ONLY"}'
host="tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs"
for n in 1 2; do
  out="$(printf '%s\n' "$request" | node "$host" --single-request)"
  node -e '
    "use strict";
    const v=JSON.parse(process.argv[1]);
    if(v.status!=="M13K_SYNTHETIC_ENCRYPTED_RESTART_PASS"
       ||v.syntheticRoundTripVerified!==true
       ||v.productionActivation!==false
       ||v.persistAuthorized!==false
       ||v.writeAuthorized!==false
       ||v.keyReleaseAuthorized!==false)process.exit(1);
  ' "$out"
  test ! -e "$HOME/m13g-disposable/draft.enc"
  # Key removed by the host, never enumerate or clear unrelated secrets.
  if secret-tool lookup service post-apollo-m13g-ci id M13gSynthetic001 >/dev/null 2>&1; then
    printf '%s\n' "M13K_UNEXPECTED_KEY_REMAINS" >&2
    exit 1
  fi
done
# Quickshell keeps its QProcess stdin open after sending one request.
# Unlike the pipeline above, this parent keeps the write descriptor OPEN
# and insists that the actual Node host exits anyway.
held="tests/tasks/fixtures/TaskEncryptedDraftHeldStdinM13n.cjs"
test "$(node "$held" --held-open-malformed)" =     "M13N_HELD_STDIN_MALFORMED_CHILD_EXIT_PASS"
test "$(node "$held" --held-open-valid)" =     "M13N_HELD_STDIN_ENCRYPTED_CHILD_EXIT_PASS"
test ! -e "$HOME/m13g-disposable/draft.enc"
if secret-tool lookup service post-apollo-m13g-ci id M13gSynthetic001 >/dev/null 2>&1; then
  printf '%s\n' "M13N_UNEXPECTED_TEST_KEY_REMAINS" >&2
  exit 1
fi
printf '%s\n' "M13N_HELD_STDIN_AND_PRIVATE_CLEANUP_PASS"
printf '%s\n' "M13K_PRIVATE_HOST_IPC_AND_CLEANUP_PASS"
