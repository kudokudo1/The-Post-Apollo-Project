#!/usr/bin/env bash
set -euo pipefail

# M26-C CI: real production card + real X11 pointer events on disposable
# Fedora Xvfb. No compositor, personal data, production shell, or user HOME.
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
qs_bin="$(command -v quickshell || true)"
[ -n "$qs_bin" ] || { echo 'M26C_UI_FAIL // quickshell absent' >&2; exit 2; }
for program in timeout xdotool Xvfb node; do
  command -v "$program" >/dev/null || {
    echo "M26C_UI_FAIL // required program absent: $program" >&2
    exit 2
  }
done

work="$(mktemp -d /tmp/weather-m26c-fedora.XXXXXXXX)"
qs_pid=""
xvfb_pid=""
cleanup() {
  [ -z "$qs_pid" ] || kill "$qs_pid" 2>/dev/null || true
  [ -z "$xvfb_pid" ] || kill "$xvfb_pid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" \
  "$work/cache" "$work/config-root" "$work/config/widgets/weather" \
  "$work/config/services/weather"
cp "$repo_root/tests/weather/fixtures/M26CFedoraDossierCard.qml" \
   "$work/config/shell.qml"
cp -a "$repo_root/components" "$work/config/components"
cp "$repo_root/widgets/weather/StationEventContextCard.qml" \
   "$work/config/widgets/weather/"
for name in StationDossierPreviewPolicy.js \
    StationDossierCapturePolicy.js StationDossierSerializationPolicy.js; do
  cp "$repo_root/widgets/weather/$name" "$work/config/widgets/weather/"
done
for name in WeatherDossierArchiveStore.qml \
    WeatherDossierArchivePolicy.js WeatherRuntimePolicy.js; do
  cp "$repo_root/services/weather/$name" "$work/config/services/weather/"
done

# This virtual X server exists only inside the CI container.
Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xvfb_pid="$!"
export DISPLAY=:99
export QT_QPA_PLATFORM=xcb
export QT_QUICK_BACKEND=software
sleep 0.4
if ! kill -0 "$xvfb_pid" 2>/dev/null; then
  cat "$work/xvfb.log"
  echo 'M26C_UI_FAIL // isolated Xvfb did not start' >&2
  exit 1
fi

log="$work/fedora-card.log"
timeout --signal=TERM --kill-after=3s 30s \
    env -u WAYLAND_DISPLAY \
    HOME="$work/home" \
    XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" \
    XDG_CONFIG_HOME="$work/config-root" \
    XDG_CACHE_HOME="$work/cache" \
    QT_LOGGING_RULES="qml.debug=true" \
    "$qs_bin" --no-color --log-rules "qml.debug=true" \
      -p "$work/config/shell.qml" \
    >"$log" 2>&1 &
qs_pid="$!"

wait_marker() {
  local wanted="$1"
  local limit=150
  local i
  for ((i=0; i<limit; i++)); do
    if grep -F "$wanted" "$log" >/dev/null 2>&1; then
      return 0
    fi
    if grep -F "M26C_UI_FAIL" "$log" >/dev/null 2>&1 \
        || ! kill -0 "$qs_pid" 2>/dev/null; then
      cat "$log"
      echo "M26C_UI_FAIL // process exited or reported error waiting for $wanted" >&2
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "M26C_UI_FAIL // timeout waiting for $wanted" >&2
  return 1
}

wait_marker "M26C_UI_READY // SAVE x="
wid="$(xdotool search --onlyvisible --name 'M26C-DOSSIER-TEST' | head -n 1)"
[ -n "$wid" ] || { cat "$log"; echo 'M26C_UI_FAIL // X11 test window absent' >&2; exit 1; }
xdotool windowmove "$wid" 0 0
point="$(sed -n 's/.*M26C_UI_READY \/\/ SAVE x=\([0-9]*\) y=\([0-9]*\).*/\1 \2/p' "$log" | tail -n 1)"
[ -n "$point" ] || { cat "$log"; echo 'M26C_UI_FAIL // no pointer geometry' >&2; exit 1; }
read -r click_x click_y <<< "$point"

# Truly deliver a disabled native left-click, not a QML signal shortcut.
xdotool mousemove --window "$wid" "$click_x" "$click_y" click 1
sleep 0.2
if grep -F "M26C_UI_REQUEST" "$log" >/dev/null; then
  cat "$log"
  echo 'M26C_UI_FAIL // disabled ActionButton accepted native click' >&2
  exit 1
fi
echo 'M26C_UI_PASS // DISABLED_POINTER_IGNORED'

wait_marker "M26C_UI_ARMED // POINTER_CLICK_NOW"
xdotool mousemove --window "$wid" "$click_x" "$click_y" click 1
wait_marker "M26C_UI_PASS // ENABLED_POINTER_SAVED"

set +e
wait "$qs_pid"
rc=$?
set -e
qs_pid=""
cat "$log"
if [ "$rc" -ne 0 ] || grep -F 'M26C_UI_FAIL' "$log" >/dev/null; then
  echo "M26C_UI_FAIL // Quickshell process failed (rc=$rc)" >&2
  exit 1
fi
grep -F "M26C_UI_PASS // SOURCE_ARCHIVE_SEPARATE" "$log" >/dev/null

count="$(find "$work/data" -type f \
    -name 'weather-dossier-archive-v1.json' | wc -l)"
[ "$count" -eq 1 ] || {
  echo "M26C_UI_FAIL // one dossier archive expected, got $count" >&2
  find "$work/data" -type f -print >&2
  exit 1
}
archive="$(find "$work/data" -type f \
    -name 'weather-dossier-archive-v1.json' -print -quit)"
node - "$archive" <<'NODE'
const fs = require('node:fs');
const assert = require('node:assert/strict');
const doc = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
assert.equal(doc.schema, 'post-apollo.weather-dossier-archive.v1');
assert.equal(doc.version, 1);
assert.equal(doc.entries.length, 1);
assert.equal(doc.entries[0].sourceId, 'gdacs');
assert.equal(doc.entries[0].eventId, 'GDACS-M26C-CLICK');
assert.equal(doc.revision, 1);
const packet = JSON.parse(doc.entries[0].transport);
assert.equal(packet.candidate.semantics.incidentMerge, false);
assert.equal(packet.candidate.semantics.persistence, 'NONE');
console.log('M26C_UI_PASS // ON_DISK_DOSSIER_IDENTITY_VERIFIED');
NODE
if find "$work/data" -type f -name 'weather-event-archive-v1.json' |
    grep . >/dev/null; then
  echo "M26C_UI_FAIL // source-native archive unexpectedly written" >&2
  exit 1
fi
echo 'M26C_UI_PASS // FEDORA_XVFB_CARD_POINTER_STORAGE'
