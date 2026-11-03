#!/usr/bin/env bash
set -euo pipefail

# M26-B: native Quickshell with an isolated configuration and XDG sandbox.
# NEVER point this at ~/.config/quickshell or the running desktop.
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
qs_bin="$(command -v quickshell || true)"
if [ -z "$qs_bin" ]; then
  echo 'M26_NATIVE_FAIL // quickshell executable unavailable' >&2
  exit 2
fi
command -v timeout >/dev/null 2>&1 || {
  echo 'M26_NATIVE_FAIL // timeout executable unavailable' >&2
  exit 2
}
work="$(mktemp -d "/tmp/weather-m26b-native.XXXXXXXX")"
cleanup() { rm -rf -- "$work"; }
trap cleanup EXIT

install -d -m 700 "$work/home" "$work/run" "$work/data" \
    "$work/cache" "$work/config-root" "$work/config/services/weather" \
    "$work/config/widgets/weather"
cp "$repo_root/tests/weather/fixtures/M26NativeDossierShell.qml" \
   "$work/config/shell.qml"
for name in WeatherDossierArchiveStore.qml WeatherDossierArchivePolicy.js; do
  cp "$repo_root/services/weather/$name" \
     "$work/config/services/weather/$name"
done
for name in StationDossierPreviewPolicy.js \
  StationDossierCapturePolicy.js \
  StationDossierSerializationPolicy.js; do
  cp "$repo_root/widgets/weather/$name" \
     "$work/config/widgets/weather/$name"
done

run_phase() {
  local phase="$1"
  local marker="$2"
  local log="$work/$phase.log"
  local rc=0
  timeout --signal=TERM --kill-after=3s 25s \
    env -u DISPLAY -u WAYLAND_DISPLAY \
      HOME="$work/home" \
      XDG_RUNTIME_DIR="$work/run" \
      XDG_DATA_HOME="$work/data" \
      XDG_CONFIG_HOME="$work/config-root" \
      XDG_CACHE_HOME="$work/cache" \
      QT_QPA_PLATFORM=offscreen \
      M26_NATIVE_PHASE="$phase" \
      "$qs_bin" --no-color -p "$work/config/shell.qml" \
      > "$log" 2>&1 || rc=$?
  cat "$log"
  if [ "$rc" -ne 0 ] || ! grep -F "M26_NATIVE_PASS // $marker" "$log" > /dev/null; then
    echo "M26_NATIVE_FAIL // phase=$phase process_exit=$rc" >&2
    return 1
  fi
  if grep -F 'M26_NATIVE_FAIL' "$log" > /dev/null; then
    echo "M26_NATIVE_FAIL // contradictory failure in phase $phase" >&2
    return 1
  fi
}

# Fresh boot must produce a single operator-like explicit dossier capture.
run_phase create CREATE_CALLBACK_SAVED

archive_count="$(find "$work/data" -type f \
  -name 'weather-dossier-archive-v1.json' | wc -l)"
if [ "$archive_count" -ne 1 ]; then
  echo "M26_NATIVE_FAIL // expected one dossier file, got $archive_count" >&2
  find "$work/data" -type f -print >&2
  exit 1
fi
archive_path="$(find "$work/data" -type f \
  -name 'weather-dossier-archive-v1.json' -print -quit)"
node - "$archive_path" <<'NODE'
"use strict";
const fs = require("node:fs");
const assert = require("node:assert/strict");
const doc = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
assert.equal(doc.schema, "post-apollo.weather-dossier-archive.v1");
assert.equal(doc.version, 1);
assert.equal(doc.revision, 1);
assert.equal(doc.entries.length, 1);
assert.equal(doc.entries[0].sourceId, "gdacs");
assert.equal(doc.entries[0].eventId, "GDACS-M26-NATIVE");
const packet = JSON.parse(doc.entries[0].transport);
assert.equal(packet.candidate.semantics.incidentMerge, false);
assert.equal(packet.candidate.semantics.persistence, "NONE");
console.log("M26_NATIVE_DISK // FIRST_WRITE_VALID");
NODE

# Separate process, same isolated data roots, checks genuine FileView reload.
before_sha="$(sha256sum "$archive_path" | cut -d ' ' -f 1)"
run_phase reload RELOAD_READBACK_VALIDATED
after_sha="$(sha256sum "$archive_path" | cut -d ' ' -f 1)"
[ "$before_sha" = "$after_sha" ] || {
  echo 'M26_NATIVE_FAIL // reload unexpectedly changed file' >&2
  exit 1
}

# Replace ONLY the disposable file with broken JSON. Actual FileView
# must refuse it and the attempted capture must not overwrite those bytes.
printf '{bad-json' > "$archive_path"
bad_sha="$(sha256sum "$archive_path" | cut -d ' ' -f 1)"
run_phase corrupt CORRUPT_FILE_WRITE_REFUSED
new_sha="$(sha256sum "$archive_path" | cut -d ' ' -f 1)"
[ "$bad_sha" = "$new_sha" ] || {
  echo 'M26_NATIVE_FAIL // corrupt archive was overwritten' >&2
  exit 1
}
echo 'M26_NATIVE_PASS // ISOLATED_FILEVIEW_SAVE_RELOAD_REFUSAL'
