#!/usr/bin/env bash
set -euo pipefail
# CPU++ C1 isolated native Quickshell click test; never touches user desktop.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool timeout; do
  command -v "$cmd" >/dev/null || { echo "C1_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/postapollo-c1-connections.XXXXXXXX)"
pid=""
xpid=""
cleanup() {
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" "$work/cache" \
  "$work/config-home" "$work/config/widgets"
cp -a "$repo/components" "$work/config/components"
cp -a "$repo/widgets/cpuplus" "$work/config/widgets/cpuplus"
cp -a "$repo/services" "$work/config/services"
cp "$repo/tests/cpuplus/fixtures/C1ConnectionsNative.qml" \
  "$work/config/shell.qml"

Xvfb :99 -screen 0 1600x1000x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }
log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 38s \
  env -u WAYLAND_DISPLAY \
  -u POST_APOLLO_FIRMS_MAP_KEY \
  HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
  quickshell --no-color --log-rules "qml.debug=true" \
  -p "$work/config/shell.qml" >"$log" 2>&1 &
pid="$!"

wait_for() {
  local marker="$1"
  for ((i=0; i<240; i++)); do
    grep -F "$marker" "$log" >/dev/null 2>&1 && return 0
    if grep -F "C1_FAIL" "$log" >/dev/null 2>&1 || \
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"
      echo "C1_FAIL // exited while waiting for $marker" >&2
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "C1_FAIL // timeout waiting for $marker" >&2
  return 1
}
click() {
  local name="$1" coords x y
  coords="$(grep -F "C1_${name}_READY // x=" "$log" | tail -n 1 |
    sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
  [ -n "$coords" ] || { echo "C1_FAIL // missing geometry: $name"; exit 1; }
  read -r x y <<<"$coords"
  xdotool mousemove --window "$wid" "$x" "$y" click 1
}
wait_for "C1_FIRMS_BUTTON_READY // x="
wid="$(xdotool search --onlyvisible --name 'C1-CONNECTIONS' | head -n 1)"
[ -n "$wid" ] || { cat "$log"; echo "C1_FAIL // native window missing"; exit 1; }
xdotool windowmove "$wid" 0 0
click FIRMS_BUTTON
wait_for "C1_GUIDE_BUTTON_READY // x="
click GUIDE_BUTTON
wait_for "C1_KEYRING_BUTTON_READY // x="
click KEYRING_BUTTON
wait_for "C2A_PASS // READONLY_KEYRING_PROBE // "
wait_for "C1_REVIEW_ACCESS_READY // x="
click REVIEW_ACCESS
wait_for "C1_DISMISS_REVIEW_READY // x="
click DISMISS_REVIEW
wait_for "C2E_PASS // NATIVE_ACCESS_REVIEW_DISMISS_NO_GRANT"
wait_for "C1_STATUS_OPEN_READY // x="
click STATUS_OPEN
wait_for "C1_HOST_INSPECT_READY // x="
click HOST_INSPECT
wait_for "C2I_PASS // NATIVE_INSPECT_LOCAL_HOST_OFFLINE_NO_GRANTS"
wait_for "C1_STATUS_CLOSE_READY // x="
click STATUS_CLOSE
wait_for "C2G_PASS // NATIVE_OFFLINE_SIMULATED_STATES_NO_GRANTS"
wait_for "C1_SOCIAL_BUTTON_READY // x="
click SOCIAL_BUTTON
wait_for "C1_RELOAD_BUTTON_READY // x="
click RELOAD_BUTTON
wait_for "C1_PASS // NATIVE_PROVIDER_SELECT_GUIDE_SOCIAL_RELOAD"

set +e
wait "$pid"
rc="$?"
set -e
pid=""
cat "$log"
[ "$rc" -eq 0 ] || { echo "C1_FAIL // Quickshell exit $rc"; exit 1; }
# No new account, key, or status file may appear in the disposable tree.
for name in connections-v1.json credentials.json api-keys.json; do
  [ -z "$(find "$work/data" -name "$name" -print -quit)" ] || {
    echo "C1_FAIL // unexpected writable connection file: $name" >&2; exit 1;
  }
done
echo "C1_PASS // NATIVE_READONLY_CPU_CONNECTIONS_NO_SECRET_WRITER"
