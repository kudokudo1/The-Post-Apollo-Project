#!/usr/bin/env bash
set -euo pipefail
# M26-D CI-only. Real StationDiscovery with synthetic GDACS data, isolated
# virtual X11 display, temporary config and HOME. No operator workstation.
root="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool node timeout; do
  command -v "$cmd" >/dev/null || { echo "M26D_FAIL // $cmd missing"; exit 2; }
done
work="$(mktemp -d /tmp/weather-m26d-map.XXXXXXXX)"
qs_pid=""
x_pid=""
cleanup() {
  [ -z "$qs_pid" ] || kill "$qs_pid" 2>/dev/null || true
  [ -z "$x_pid" ] || kill "$x_pid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" "$work/cache" \
  "$work/config-home" "$work/config" "$work/config/widgets" "$work/config/services"
cp -a "$root/components" "$work/config/components"
cp -a "$root/widgets/weather" "$work/config/widgets/weather"
cp -a "$root/services/weather" "$work/config/services/weather"
cp "$root/tests/weather/fixtures/M26DDiscoveryMap.qml" "$work/config/shell.qml"
cp "$root/tests/weather/fixtures/M26DGdacsSource.qml" \
   "$work/config/services/weather/GdacsService.qml"

Xvfb :99 -screen 0 1600x1200x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
x_pid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$x_pid" || { cat "$work/xvfb.log"; exit 1; }

log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 30s \
  env -u WAYLAND_DISPLAY \
    HOME="$work/home" \
    XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" \
    XDG_CONFIG_HOME="$work/config-home" \
    XDG_CACHE_HOME="$work/cache" \
    QT_LOGGING_RULES="qml.debug=true" \
    quickshell --no-color --log-rules "qml.debug=true" \
      -p "$work/config/shell.qml" >"$log" 2>&1 &
qs_pid="$!"

wait_for() {
  local label="$1"
  for ((i=0; i<180; i++)); do
    if grep -F "$label" "$log" >/dev/null 2>&1; then return 0; fi
    if grep -F "M26D_FAIL" "$log" >/dev/null 2>&1 ||
       ! kill -0 "$qs_pid" 2>/dev/null; then
      cat "$log"
      echo "M26D_FAIL // exited or errored waiting for $label"
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "M26D_FAIL // timeout waiting for $label"
  return 1
}
click_at_marker() {
  local tag="$1" point x y
  point="$(grep -F "M26D_"$tag"_READY // x=" "$log" | tail -n 1 |
     sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
  [ -n "$point" ] || { echo "M26D_FAIL // no $tag position"; exit 1; }
  read -r x y <<<"$point"
  xdotool mousemove --window "$wid" "$x" "$y" click 1
}

wait_for "M26D_MAP_READY // x="
wid="$(xdotool search --onlyvisible --name 'M26D-MAP-TEST' | head -n 1)"
[ -n "$wid" ] || { cat "$log"; echo 'M26D_FAIL // no virtual window'; exit 1; }
xdotool windowmove "$wid" 0 0
[ "$(find "$work/data" -name weather-dossier-archive-v1.json | wc -l)" -eq 0 ] ||
 { echo "M26D_FAIL // eager archive before map selection"; exit 1; }
click_at_marker MAP
wait_for "M26D_SAVE_READY // x="
[ "$(find "$work/data" -name weather-dossier-archive-v1.json | wc -l)" -eq 0 ] ||
 { echo "M26D_FAIL // selection auto-wrote archive"; exit 1; }
click_at_marker SAVE
wait_for "M26D_PASS // MAP_SELECTED_AND_DOSSIER_SAVED"
set +e
wait "$qs_pid"
rc=$?
set -e
qs_pid=""
cat "$log"
[ "$rc" -eq 0 ] || { echo "M26D_FAIL // quickshell exit=$rc"; exit 1; }
[ "$(find "$work/data" -name weather-dossier-archive-v1.json | wc -l)" -eq 1 ] ||
 { echo "M26D_FAIL // expected exactly one dossier file"; exit 1; }
p="$(find "$work/data" -name weather-dossier-archive-v1.json -print -quit)"
node - "$p" <<'NODE'
const assert=require("node:assert/strict");
const fs=require("node:fs");
const record=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
assert.equal(record.schema,"post-apollo.weather-dossier-archive.v1");
assert.equal(record.revision,1);
assert.equal(record.entries.length,1);
assert.equal(record.entries[0].sourceId,"gdacs");
assert.equal(record.entries[0].eventId,"FL:M26D:1");
const packet=JSON.parse(record.entries[0].transport);
assert.equal(packet.candidate.semantics.incidentMerge,false);
assert.equal(packet.candidate.semantics.persistence,"NONE");
console.log("M26D_PASS // EXACT_PROVIDER_IDENTITY_ON_DISK");
NODE
[ "$(find "$work/data" -name weather-event-archive-v1.json | wc -l)" -eq 0 ] ||
 { echo "M26D_FAIL // source-native archive overwritten"; exit 1; }
echo 'M26D_PASS // ACTUAL_MAP_SELECTION_TO_DOSSIER_STORAGE'
