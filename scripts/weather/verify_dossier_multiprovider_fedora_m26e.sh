#!/usr/bin/env bash
set -euo pipefail
# Native Xvfb verification; only temp config/files, four processes, one archive.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool node timeout; do
  command -v "$cmd" >/dev/null || exit 2
done
temp="$(mktemp -d /tmp/weather-m26e.XXXXXXXX)"
pid="" xpid=""
cleanup() {
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$temp"
}
trap cleanup EXIT
install -d -m 700 "$temp/home" "$temp/run" "$temp/data" "$temp/cache" \
  "$temp/config-home" "$temp/config/widgets" "$temp/config/services"
cp -a "$repo/components" "$temp/config/components"
cp -a "$repo/widgets/weather" "$temp/config/widgets/weather"
cp -a "$repo/services/weather" "$temp/config/services/weather"
cp "$repo/tests/weather/fixtures/M26EMultiSourceMap.qml" "$temp/config/shell.qml"
cp "$repo/tests/weather/fixtures/M26EGdacsService.qml" \
  "$temp/config/services/weather/GdacsService.qml"
cp "$repo/tests/weather/fixtures/M26EStationDiscoveryService.qml" \
  "$temp/config/services/weather/StationDiscoveryService.qml"
cp "$repo/tests/weather/fixtures/M26EFirmsHotspotService.qml" \
  "$temp/config/services/weather/FirmsHotspotService.qml"
Xvfb :99 -screen 0 1600x1200x24 -nolisten tcp >"$temp/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$temp/xvfb.log"; exit 1; }
wait_for() {
  local wanted="$1"
  for ((n=0;n<180;n++)); do
    grep -F "$wanted" "$log" >/dev/null 2>&1 && return 0
    if grep -F 'M26E_FAIL' "$log" >/dev/null 2>&1 ||
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"; echo "M26E_FAIL // exited before $wanted" >&2; exit 1
    fi
    sleep 0.1
  done
  cat "$log"; echo "M26E_FAIL // timeout $wanted" >&2; exit 1
}
click_marker() {
  local label="$1" point x y
  point="$(grep -F "M26E_"$label"_READY // source=$source x=" "$log" |
    tail -n 1 | sed -E 's/.* x=([0-9]+) y=([0-9]+).*/\1 \2/')"
  [ -n "$point" ] || { echo "M26E_FAIL // no $label coordinates" >&2; exit 1; }
  read -r x y <<< "$point"
  xdotool mousemove --window "$window" "$x" "$y" click 1
}
previous_sha=""
archive=""
for source in gdacs usgs eonet firms; do
  case "$source" in
    gdacs) ordinal=1;; usgs) ordinal=2;; eonet) ordinal=3;; firms) ordinal=4;;
  esac
  log="$temp/$source.log"
  echo "M26E_CASE // $source $ordinal"
  timeout --signal=TERM --kill-after=3s 30s \
    env -u WAYLAND_DISPLAY \
      HOME="$temp/home" XDG_RUNTIME_DIR="$temp/run" \
      XDG_DATA_HOME="$temp/data" XDG_CONFIG_HOME="$temp/config-home" \
      XDG_CACHE_HOME="$temp/cache" QT_LOGGING_RULES="qml.debug=true" \
      M26E_SOURCE="$source" M26E_ORDINAL="$ordinal" \
      quickshell --no-color --log-rules "qml.debug=true" \
      -p "$temp/config/shell.qml" >"$log" 2>&1 &
  pid="$!"
  wait_for "M26E_MAP_READY // source=$source x="
  window="$(xdotool search --onlyvisible --name 'M26E-MAP-TEST' | head -n 1)"
  [ -n "$window" ] || { cat "$log"; exit 1; }
  xdotool windowmove "$window" 0 0
  click_marker MAP
  wait_for "M26E_SAVE_READY // source=$source x="
  # Selecting a map marker is read-only, even with earlier saved dossiers.
  if [ "$ordinal" -eq 1 ]; then
    [ -z "$(find "$temp/data" -name weather-dossier-archive-v1.json -print -quit)" ] ||
      { echo 'M26E_FAIL // selection wrote first dossier'; exit 1; }
  else
    [ "$previous_sha" = "$(sha256sum "$archive" | cut -d ' ' -f1)" ] ||
      { echo 'M26E_FAIL // selection mutated prior archive'; exit 1; }
  fi
  click_marker SAVE
  wait_for "M26E_PASS // SOURCE=$source REVISION=$ordinal EXACT_PROVIDER_EVENT_KEY_PERSISTED"
  set +e
  wait "$pid"
  rc=$?
  set -e
  pid=""
  cat "$log"
  [ "$rc" -eq 0 ] || { echo "M26E_FAIL // quickshell exit=$rc"; exit 1; }
  count="$(find "$temp/data" -name weather-dossier-archive-v1.json | wc -l)"
  [ "$count" -eq 1 ] || { echo "M26E_FAIL // file count=$count"; exit 1; }
  archive="$(find "$temp/data" -name weather-dossier-archive-v1.json -print -quit)"
  node - "$archive" "$ordinal" <<'NODE'
const fs=require("node:fs"),assert=require("node:assert/strict");
const a=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const count=Number(process.argv[3]), sources=["gdacs","usgs","eonet","firms"];
assert.equal(a.schema,"post-apollo.weather-dossier-archive.v1");
assert.equal(a.version,1);assert.equal(a.revision,count);
assert.equal(a.entries.length,count);
for(let i=0;i<count;i++) {
  const r=a.entries[i];
  assert.equal(r.sourceId,sources[i]);
  assert.equal(r.eventId,"M26E-SHARED");
  assert.equal(r.sequence,i+1);
  const v=JSON.parse(r.transport);
  assert.equal(v.candidate.selectedEvent.sourceId,sources[i]);
  assert.equal(v.candidate.selectedEvent.eventId,"M26E-SHARED");
  assert.equal(v.candidate.semantics.incidentMerge,false);
  assert.equal(v.candidate.semantics.persistence,"NONE");
}
assert.equal(new Set(a.entries.map(x=>x.sourceId+"|"+x.eventId)).size,count);
console.log("M26E_DISK_PASS // DISTINCT_PROVIDER_KEYS="+count);
NODE
  [ -z "$(find "$temp/data" -name weather-event-archive-v1.json -print -quit)" ] ||
    { echo 'M26E_FAIL // source-native archive written'; exit 1; }
  previous_sha="$(sha256sum "$archive" | cut -d ' ' -f1)"
done
echo 'M26E_PASS // FOUR_PROVIDER_MAP_SELECTIONS_DISTINCT_AND_PERSISTENT'
