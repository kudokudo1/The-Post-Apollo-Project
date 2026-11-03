#!/usr/bin/env bash
set -euo pipefail
# M28-A CI-only: actual SUBJECTS Navigator + EARTH map marker/clear clicks.
# No operator desktop, real feeds, archive writer or live Quickshell state.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool node timeout; do
  command -v "$cmd" >/dev/null || { echo "M28A_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/weather-m28a-media-earth.XXXXXXXX)"
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
cp -a "$repo/widgets/weather" "$work/config/widgets/weather"
cp -a "$repo/services" "$work/config/services"
cp "$repo/tests/weather/fixtures/M28AMediaEarthMentions.qml" "$work/config/shell.qml"
# Only the temporary test tree substitutes fake, network-free providers.
cp "$repo/tests/weather/fixtures/M26DGdacsSource.qml" \
   "$work/config/services/weather/GdacsService.qml"
cp "$repo/tests/weather/fixtures/M26EStationDiscoveryService.qml" \
   "$work/config/services/weather/StationDiscoveryService.qml"

Xvfb :99 -screen 0 1600x1200x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }
log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 32s \
  env -u WAYLAND_DISPLAY \
  HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
  quickshell --no-color --log-rules "qml.debug=true" \
  -p "$work/config/shell.qml" >"$log" 2>&1 &
pid="$!"

wait_for() {
  local marker="$1"
  for ((i=0;i<185;i++)); do
    grep -F "$marker" "$log" >/dev/null 2>&1 && return 0
    if grep -F 'M28A_FAIL' "$log" >/dev/null 2>&1 ||
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"
      echo "M28A_FAIL // exited while waiting for $marker" >&2
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "M28A_FAIL // timed out waiting for $marker" >&2
  return 1
}
click() {
  local name="$1" coords x y
  coords="$(grep -F "M28A_"$name"_READY // x=" "$log" | tail -n 1 |
    sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
  [ -n "$coords" ] || { echo "M28A_FAIL // missing $name geometry"; exit 1; }
  read -r x y <<<"$coords"
  xdotool mousemove --window "$wid" "$x" "$y" click 1
}
wait_for "M28A_MARKER_READY // x="
wid="$(xdotool search --onlyvisible --name 'M28A-MEDIA-EARTH' | head -n 1)"
[ -n "$wid" ] || { cat "$log"; echo "M28A_FAIL // window not found"; exit 1; }
xdotool windowmove "$wid" 0 0
click MARKER
wait_for "M28A_CLEAR_READY // x="
click CLEAR
wait_for "M28A_PASS // SUBJECT_NATIVE_MEDIA_TO_EARTH_NO_CLASSIC"
set +e
wait "$pid"
rc="$?"
set -e
pid=""
cat "$log"
[ "$rc" -eq 0 ] || { echo "M28A_FAIL // Quickshell exit $rc"; exit 1; }
grep -F 'M28A_PASS // NATIVE_NEWS_MARKER_INSPECTED_NOT_EVENT' "$log" >/dev/null
for filename in weather-dossier-archive-v1.json weather-event-archive-v1.json; do
  [ -z "$(find "$work/data" -name "$filename" -print -quit)" ] || {
    echo "M28A_FAIL // unexpected $filename writer"; exit 1;
  }
done
echo 'M28A_PASS // MEDIA_TO_EARTH_MAP_WITHOUT_CLASSIC_OR_WRITES'
