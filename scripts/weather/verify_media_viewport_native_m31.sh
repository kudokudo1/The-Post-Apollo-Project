#!/usr/bin/env bash
set -euo pipefail
# Disposable CI-only Quickshell/QML geometry test. Never touches Fedora host.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for tool in quickshell Xvfb timeout; do
  command -v "$tool" >/dev/null || { echo "M31_FAIL // missing $tool" >&2; exit 2; }
done
work="$(mktemp -d /tmp/weather-m31-viewport.XXXXXXXX)"
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
cp -a "$repo/widgets/weather" "$work/config/widgets/weather"
# The real MEDIA pane imports services/media for RADIO, plus NEWS/Weather
# shared helpers. Even inactive Component source types must resolve at parse.
# Copy existing services into the isolated fixture, never install anything.
cp -a "$repo/services/." "$work/config/services/"
cp "$repo/tests/weather/fixtures/M31MediaViewport.qml" "$work/config/shell.qml"

Xvfb :95 -screen 0 1450x940x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:95 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log" >&2; exit 1; }
log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 23s \
  env -u WAYLAND_DISPLAY \
  HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
  quickshell --no-color --log-rules "qml.debug=true" \
    -p "$work/config/shell.qml" >"$log" 2>&1 &
pid="$!"
set +e
wait "$pid"
rc="$?"
set -e
pid=""
cat "$log"
if [ "$rc" -ne 0 ] || ! grep -Fq 'M31_PASS // NATIVE_MEDIA_VIEWPORT' "$log" || \
   grep -Eq 'M31_FAIL|ReferenceError|TypeError|Cannot assign to non-existent property' "$log"; then
  echo "M31_FAIL // native QML geometry smoke did not pass, exit=$rc" >&2
  exit 1
fi
echo "M31_NATIVE_MEDIA_GEOMETRY: actual_Quickshell_QML=1 nested_viewport=1 no_browser=1 PASS"
