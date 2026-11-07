#!/usr/bin/env bash
set -euo pipefail
# Synthetic Fedora Quickshell validation: real QML binding, no real owners.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb timeout; do
  command -v "$cmd" >/dev/null ||
    { echo "U2_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/favorites-u2.XXXXXXXX)"
xpid=""
cleanup() {
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" \
  "$work/cache" "$work/config-home" "$work/config/services/favorites"
cp -a "$repo/components" "$work/config/components"
cp "$repo/services/favorites/"* "$work/config/services/favorites/"
cp "$repo/tests/favorites/fixtures/FavoritesU2NativeProbe.qml" \
  "$work/config/shell.qml"
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.4
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }

set +e
timeout --signal=TERM --kill-after=3s 14s \
  env -u WAYLAND_DISPLAY HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" \
  quickshell --no-color --log-rules "qml.debug=true" \
  -p "$work/config/shell.qml" >"$work/quickshell.log" 2>&1
rc="$?"
set -e
cat "$work/quickshell.log"
if [ "$rc" -ne 0 ] || grep -F "U2_FAIL" "$work/quickshell.log" >/dev/null; then
  echo "U2_FAIL // native process/error marker rc=$rc"; exit 1
fi
for marker in "U2_PASS // INITIAL_THREE_OWNERS" \
              "U2_PASS // REACTIVE_THREE_OWNER_UPDATES" \
              "U2_PASS // NATIVE_READ_ONLY_CATALOG"; do
  grep -F "$marker" "$work/quickshell.log" >/dev/null ||
    { echo "U2_FAIL // missing marker $marker"; exit 1; }
done
if find "$work/data" -type f | grep -q .; then
  echo "U2_FAIL // unexpected persistence in read-only snapshot"; exit 1
fi
echo "U2_PASS // NATIVE_QML_REACTIVE_NO_FILES"
