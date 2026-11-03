#!/usr/bin/env bash
set -euo pipefail

# CI-only M26-C. Runs the real StationEventContextCard offscreen with a
# disposable FileView directory. Never uses the operator's Quickshell tree.
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
qs_bin="$(command -v quickshell || true)"
[ -n "$qs_bin" ] || { echo 'M26C_UI_FAIL // quickshell absent' >&2; exit 2; }
command -v timeout >/dev/null || exit 2
command -v node >/dev/null || exit 2

work="$(mktemp -d /tmp/weather-m26c-fedora.XXXXXXXX)"
trap 'rm -rf -- "$work"' EXIT
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

log="$work/fedora-card.log"
rc=0
timeout --signal=TERM --kill-after=3s 35s \
    env -u DISPLAY -u WAYLAND_DISPLAY \
    HOME="$work/home" \
    XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" \
    XDG_CONFIG_HOME="$work/config-root" \
    XDG_CACHE_HOME="$work/cache" \
    QT_QPA_PLATFORM=offscreen \
    QT_QUICK_BACKEND=software \
    "$qs_bin" --no-color -p "$work/config/shell.qml" \
    >"$log" 2>&1 || rc=$?
cat "$log"

if [ "$rc" -ne 0 ] || grep -E 'M26C_UI_FAIL|FAIL!' "$log" >/dev/null; then
  echo "M26C_UI_FAIL // Qt process or assertion failed (rc=$rc)" >&2
  exit 1
fi
for marker in DISABLED_POINTER_IGNORED ENABLED_POINTER_SAVED SOURCE_ARCHIVE_SEPARATE; do
  if ! grep -F "M26C_UI_PASS // $marker" "$log" >/dev/null; then
    echo "M26C_UI_FAIL // missing marker $marker" >&2
    exit 1
  fi
done

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
echo 'M26C_UI_PASS // FEDORA_OFFSCREEN_CARD_POINTER_STORAGE'
