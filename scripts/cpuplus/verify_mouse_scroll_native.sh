#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb timeout python3; do
  command -v "$cmd" >/dev/null || { echo "MOUSE_NATIVE_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/postapollo-mouse-scroll.XXXXXXXX)"
xpid=""
cleanup() {
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" "$work/cache" \
  "$work/config-home" "$work/config/widgets" "$work/config/services"
cp -a "$repo/components" "$work/config/components"
cp -a "$repo/widgets/cpuplus" "$work/config/widgets/cpuplus"
cp -a "$repo/services/input" "$work/config/services/input"
cp "$repo/tests/cpuplus/fixtures/MouseScrollNative.qml" "$work/config/shell.qml"
Xvfb :97 -screen 0 1250x900x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:97 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }
log="$work/quickshell.log"
set +e
timeout --signal=TERM --kill-after=3s 25s \
  env -u WAYLAND_DISPLAY HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
  quickshell --no-color --log-rules "qml.debug=true" \
  -p "$work/config/shell.qml" >"$log" 2>&1
rc="$?"
set -e
cat "$log"
if [ "$rc" -ne 0 ] || ! grep -q 'MOUSE_NATIVE_PASS // THREE_BAYS_STAGED_NO_HOST_MUTATION' "$log"; then
  echo "MOUSE_NATIVE_FAIL // QML stage or confirmation failed";exit 1
fi
if ! grep -q 'KITTY_NATIVE_PASS // TWO_FACTORS_STAGED_NO_CONFIG_WRITE' "$log"; then
  echo "MOUSE_NATIVE_FAIL // Kitty mode not exercised";exit 1
fi
if ! grep -q 'ZELLIJ_NATIVE_PASS // STAGED_NO_CONFIG_WRITE' "$log"; then
  echo "MOUSE_NATIVE_FAIL // Zellij mode was not exercised";exit 1
fi
if ! grep -q 'SCROLL_MODE_NATIVE_PASS // LOCK_CANCEL_AND_AUTOSCROLL_GATED' "$log"; then
  echo "MOUSE_NATIVE_FAIL // Scroll Mode consent or autoscroll gating not verified";exit 1
fi
if grep -q 'MOUSE_NATIVE_FAIL' "$log"; then exit 1; fi
if find "$work/config-home" -name 'post-apollo-*scroll*.conf' | grep -q .; then
  echo "MOUSE_NATIVE_FAIL // unexpected compositor config write";exit 1
fi
echo "MOUSE_NATIVE_PASS // ISOLATED_QML"
