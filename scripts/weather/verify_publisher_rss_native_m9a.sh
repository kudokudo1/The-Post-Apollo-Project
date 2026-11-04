#!/usr/bin/env bash
set -euo pipefail
# M9a native Fedora Quickshell smoke. All writes under temporary CI path.
# Real RSS publisher hosts are NEVER contacted: the production helper path
# is replaced with a fixed synthetic Python fixture in the copied config.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool timeout python3; do
  command -v "$cmd" >/dev/null || { echo "M9A_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/weather-m9a-native-rss.XXXXXXXX)"
pid=""
xpid=""
cleanup() {
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" "$work/cache" \
  "$work/config-home" "$work/config/widgets" "$work/config/scripts/weather"
cp -a "$repo/components" "$work/config/components"
cp -a "$repo/widgets/weather" "$work/config/widgets/weather"
cp -a "$repo/services" "$work/config/services"
cp "$repo/tests/weather/fixtures/M9APublisherRssNative.qml" \
  "$work/config/shell.qml"
cp "$repo/tests/weather/fixtures/M9APublisherRssFake.py" \
  "$work/config/scripts/weather/station_publisher_rss.py"

Xvfb :99 -screen 0 1600x1200x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }
log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 35s \
  env -u WAYLAND_DISPLAY HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
  quickshell --no-color --log-rules "qml.debug=true" \
  -p "$work/config/shell.qml" >"$log" 2>&1 &
pid="$!"

wait_for() {
  local marker="$1"
  for ((i=0; i<220; i++)); do
    grep -F "$marker" "$log" >/dev/null 2>&1 && return 0
    if grep -F "M9A_FAIL" "$log" >/dev/null 2>&1 || \
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"
      echo "M9A_FAIL // exited while waiting for $marker" >&2
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "M9A_FAIL // timeout waiting for $marker" >&2
  return 1
}
click_marker() {
  local name="$1" coords x y
  coords="$(grep -F "M9A_${name}_READY // x=" "$log" | tail -n 1 |
    sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
  [ -n "$coords" ] || { echo "M9A_FAIL // missing geometry: $name"; exit 1; }
  read -r x y <<<"$coords"
  xdotool mousemove --window "$wid" "$x" "$y" click 1
}
wait_for "M9A_BBC_BUTTON_READY // x="
wid="$(xdotool search --onlyvisible --name 'M9A-PUBLISHER-RSS' | head -n 1)"
[ -n "$wid" ] || { cat "$log"; echo "M9A_FAIL // native window missing"; exit 1; }
xdotool windowmove "$wid" 0 0
click_marker BBC_BUTTON
wait_for "M9A_BBC_INSPECT_READY // x="
click_marker BBC_INSPECT
wait_for "M9A_PASS // BBC_INSPECTED_IN_STATION"
wait_for "M9A_AJ_BUTTON_READY // x="
click_marker AJ_BUTTON
wait_for "M9A_AJ_INSPECT_READY // x="
click_marker AJ_INSPECT
wait_for "M9A_PASS // BOTH_NATIVE_PUBLISHER_BUTTONS_AND_INSPECTORS"
set +e
wait "$pid"
rc="$?"
set -e
pid=""
cat "$log"
[ "$rc" -eq 0 ] || { echo "M9A_FAIL // Quickshell exit $rc"; exit 1; }
grep -F "M9A_PASS // AL_JAZEERA_INSPECTED_IN_STATION" "$log" >/dev/null
if grep -E 'api\.gdeltproject\.org|feeds\.bbci\.co\.uk|aljazeera\.com/xml/rss' "$log" >/dev/null; then
  echo "M9A_FAIL // unexpected real feed network trace" >&2
  exit 1
fi
echo "M9A_PASS // NATIVE_FAKE_ONLY_BOTH_PUBLISHER_RSS_AND_INSPECTORS"
