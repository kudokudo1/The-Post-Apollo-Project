#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb timeout python3; do
  command -v "$cmd" >/dev/null || { echo "KB_NATIVE_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/postapollo-keyboard-smoke.XXXXXXXX)"
pid=""
xpid=""
cleanup() {
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" "$work/cache" \
  "$work/config-home" "$work/config/widgets" "$work/config/services"
cp -a "$repo/components" "$work/config/components"
cp -a "$repo/widgets/cpuplus" "$work/config/widgets/cpuplus"
cp -a "$repo/services/input" "$work/config/services/input"
cp "$repo/tests/cpuplus/fixtures/KeyboardLockNative.qml" "$work/config/shell.qml"
Xvfb :98 -screen 0 1200x850x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:98 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
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
if [ "$rc" -ne 0 ] || ! grep -q "KB_NATIVE_PASS // TWO_LOCKS_SAVED_NO_HOST_INSTALL" "$log"; then
  echo "KB_NATIVE_FAIL // no verified save / QML smoke";exit 1
fi
if grep -q 'KB_NATIVE_FAIL' "$log"; then exit 1; fi
if find "$work/config-home" -name 'post-apollo-keyboard-locks.conf' | grep -q .; then
  echo "KB_NATIVE_FAIL // unexpected Sway config writer";exit 1
fi
test -z "$(find "$work/config-home" -name config -print -quit)" || {
  echo "KB_NATIVE_FAIL // unexpected compositor config";exit 1;
}
echo "KB_NATIVE_PASS // ISOLATED_QML_POLICY_PERSISTENCE"
