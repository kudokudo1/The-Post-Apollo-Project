#!/usr/bin/env bash
set -euo pipefail
# M26-F CI only: real EARTH-pane route transitions, selected GDACS event,
# native SAVE click, one disposable FileView archive, no production shell.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool node timeout; do
  command -v "$cmd" >/dev/null || {
    echo "M26F_FAIL // missing $cmd" >&2; exit 2;
  }
done
work="$(mktemp -d /tmp/weather-m26f-earth.XXXXXXXX)"
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
cp -a "$repo/services/weather" "$work/config/services/weather"
cp "$repo/tests/weather/fixtures/M26FEarthRouteContinuity.qml" \
   "$work/config/shell.qml"
# Replace ONLY the test tree's provider services: never poll live feeds.
cp "$repo/tests/weather/fixtures/M26DGdacsSource.qml" \
   "$work/config/services/weather/GdacsService.qml"
cp "$repo/tests/weather/fixtures/M26EStationDiscoveryService.qml" \
   "$work/config/services/weather/StationDiscoveryService.qml"

Xvfb :99 -screen 0 1600x1200x24 -nolisten tcp > "$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }

log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 30s \
  env -u WAYLAND_DISPLAY \
  HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
  quickshell --no-color --log-rules "qml.debug=true" \
    -p "$work/config/shell.qml" > "$log" 2>&1 &
pid="$!"

wait_for() {
  local marker="$1"
  for ((n=0;n<180;n++)); do
    grep -F "$marker" "$log" >/dev/null 2>&1 && return 0
    if grep -F 'M26F_FAIL' "$log" >/dev/null 2>&1 ||
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"; echo "M26F_FAIL // exited before $marker" >&2; return 1
    fi
    sleep 0.1
  done
  cat "$log"; echo "M26F_FAIL // timeout waiting for $marker" >&2; return 1
}
click_marker() {
  local label="$1" point x y
  point="$(grep -F "M26F_"$label"_READY // x=" "$log" |
    tail -n 1 | sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
  [ -n "$point" ] || { echo "M26F_FAIL // no $label point" >&2; exit 1; }
  read -r x y <<< "$point"
  xdotool mousemove --window "$wid" "$x" "$y" click 1
}
wait_for "M26F_MAP_READY // x="
wid="$(xdotool search --onlyvisible --name 'M26F-EARTH-TEST' | head -n 1)"
[ -n "$wid" ] || { cat "$log"; exit 1; }
xdotool windowmove "$wid" 0 0
[ -z "$(find "$work/data" -name weather-dossier-archive-v1.json -print -quit)" ] ||
  { echo 'M26F_FAIL // file existed before user action' >&2; exit 1; }
click_marker MAP
wait_for "M26F_SAVE_READY // x="
for mark in \
  'M26F_PASS // CONTEXT_ROUTE_PRESERVED_SELECTION' \
  'M26F_PASS // DOSSIERS_ROUTE_PRESERVED_PREVIEW' \
  'M26F_PASS // EARTH_MAP_RETURN_PRESERVED_VIEW'; do
  grep -F "$mark" "$log" >/dev/null || { cat "$log"; exit 1; }
done
[ -z "$(find "$work/data" -name weather-dossier-archive-v1.json -print -quit)" ] ||
  { echo 'M26F_FAIL // navigation auto-saved dossier' >&2; exit 1; }
click_marker SAVE
wait_for "M26F_PASS // EARTH_ROUTE_SELECTION_AND_HISTORY"
set +e
wait "$pid"
rc=$?
set -e
pid=""
cat "$log"
[ "$rc" -eq 0 ] || { echo "M26F_FAIL // Quickshell exit=$rc" >&2; exit 1; }
p="$(find "$work/data" -name weather-dossier-archive-v1.json -print -quit)"
[ -n "$p" ] || { echo "M26F_FAIL // dossier missing on disk" >&2; exit 1; }
node - "$p" <<'NODE'
const fs=require("node:fs"), assert=require("node:assert/strict");
const d=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
assert.equal(d.schema,"post-apollo.weather-dossier-archive.v1");
assert.equal(d.revision,1);
assert.equal(d.entries.length,1);
assert.equal(d.entries[0].sourceId,"gdacs");
assert.equal(d.entries[0].eventId,"FL:M26D:1");
const packet=JSON.parse(d.entries[0].transport);
assert.equal(packet.candidate.semantics.incidentMerge,false);
assert.equal(packet.candidate.semantics.persistence,"NONE");
console.log("M26F_PASS // EARTH_ROUTE_ON_DISK_IDENTITY");
NODE
[ -z "$(find "$work/data" -name weather-event-archive-v1.json -print -quit)" ] ||
  { echo "M26F_FAIL // source-native archive was modified" >&2; exit 1; }
echo 'M26F_PASS // NATIVE_EARTH_SUBROUTE_CONTINUITY_ONLY'
