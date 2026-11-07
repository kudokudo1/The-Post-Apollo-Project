#!/usr/bin/env bash
set -euo pipefail
# GitHub CI-only native probe, isolated from real Quickshell preferences.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool node timeout sha256sum; do
  command -v "$cmd" >/dev/null || { echo "U1_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/favorites-u1.XXXXXXXX)"
pid=""
xpid=""
cleanup() {
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT

install -d -m 700 "$work/home" "$work/run" "$work/data" \
  "$work/cache" "$work/config-home" "$work/config/services/favorites" \
  "$work/config/tests/favorites"
cp -a "$repo/components" "$work/config/components"
cp "$repo/services/favorites/FavoritesResourcePolicy.js" \
  "$repo/services/favorites/FavoritesDefaultPolicy.js" \
  "$repo/services/favorites/FavoritesDefaultStore.qml" \
  "$repo/services/favorites/qmldir" "$work/config/services/favorites/"
# Other registered singletons must be resolvable by the module loader.
cp "$repo/services/favorites/FavoritesStore.qml" \
  "$repo/services/favorites/FavoritesService.qml" \
  "$repo/services/favorites/FavoritesReadOnlyAdapters.js" \
  "$work/config/services/favorites/"
cp "$repo/tests/favorites/fixtures/FavoritesU1NativeProbe.qml" \
  "$work/config/shell.qml"

Xvfb :99 -screen 0 1024x768x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.4
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }

wait_for() {
  local marker="$1"
  for ((i=0;i<165;i++)); do
    # Errors take precedence, even if a success marker already appeared.
    if grep -F "U1_FAIL" "$log" >/dev/null 2>&1 ||
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"
      echo "U1_FAIL // exited before marker: $marker"
      return 1
    fi
    grep -F "$marker" "$log" >/dev/null 2>&1 && return 0
    sleep 0.1
  done
  cat "$log"
  echo "U1_FAIL // timeout waiting for $marker"
  return 1
}
run_phase() {
  local phase="$1" success="$2"
  log="$work/$phase.log"
  echo "U1_PHASE // $phase"
  timeout --signal=TERM --kill-after=3s 23s \
    env -u WAYLAND_DISPLAY \
    HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
    XDG_CACHE_HOME="$work/cache" U1_PHASE="$phase" \
    quickshell --no-color --log-rules "qml.debug=true" \
      -p "$work/config/shell.qml" >"$log" 2>&1 &
  pid="$!"
  if [ "$phase" = "save" ]; then
    wait_for "U1_READY // x="
    local window coords x y
    window="$(xdotool search --onlyvisible --name "U1-FAVORITES-DEFAULT" | head -n 1)"
    [ -n "$window" ] || { cat "$log"; echo "U1_FAIL // no native window"; return 1; }
    xdotool windowmove "$window" 0 0
    coords="$(grep -F "U1_READY // x=" "$log" | tail -n 1 |
      sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
    read -r x y <<<"$coords"
    [ -n "$x" ] && [ -n "$y" ] || { echo "U1_FAIL // no coords"; return 1; }
    xdotool mousemove --window "$window" "$x" "$y" click 1
    wait_for "U1_CLICK_ACCEPTED"
  fi
  wait_for "$success"
  local rc
  set +e
  wait "$pid"
  rc="$?"
  set -e
  pid=""
  cat "$log"
  if grep -F "U1_FAIL" "$log" >/dev/null 2>&1; then
    echo "U1_FAIL // phase=$phase contained failure marker"; return 1;
  fi
  [ "$rc" -eq 0 ] || { echo "U1_FAIL // phase=$phase rc=$rc"; return 1; }
}

run_phase save "U1_PASS // CLICK_RAPID_QUEUE_AND_FILEVIEW_SAVED"
saved="$(find "$work/data" -name favorites-default-v1.json -print -quit)"
[ -n "$saved" ] && [ -f "$saved" ] || {
  echo "U1_FAIL // missing default store file"; exit 1;
}
node - "$saved" <<'NODE'
const fs=require("node:fs"),assert=require("node:assert/strict");
const data=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
const key="fav1:local:demo-u1:tile:test-value";
assert.deepEqual(data,{
  schema:"post-apollo.favorites.default.v1",
  version:1,revision:6,favorites:[key],pins:[key]
});
console.log("U1_PASS // ONLY_STABLE_KEYS_ON_DISK");
NODE
for legacy in appcontrol-favorites.json weather-home-favorites-v1.json \
  time-world-favorites-v1.json places-v1.json notification-favorites.json \
  weather-radio-memory.json hospital-reception.json; do
  [ -z "$(find "$work/data" -name "$legacy" -print -quit)" ] ||
    { echo "U1_FAIL // legacy writer touched $legacy"; exit 1; }
done
before="$(sha256sum "$saved" | cut -d ' ' -f1)"
run_phase read "U1_PASS // READBACK_WITHOUT_WRITE"
after="$(sha256sum "$saved" | cut -d ' ' -f1)"
[ "$before" = "$after" ] || { echo "U1_FAIL // read changed bytes"; exit 1; }

printf '{"schema":' >"$saved"
before="$(sha256sum "$saved" | cut -d ' ' -f1)"
run_phase corrupt "U1_PASS // CORRUPT_PRESERVED"
after="$(sha256sum "$saved" | cut -d ' ' -f1)"
[ "$before" = "$after" ] || { echo "U1_FAIL // corrupt file rewritten"; exit 1; }

printf '{"schema":"post-apollo.favorites.default.v1","version":99,"revision":0,"favorites":[],"pins":[]}\n' >"$saved"
before="$(sha256sum "$saved" | cut -d ' ' -f1)"
run_phase unsupported "U1_PASS // UNSUPPORTED_PRESERVED"
after="$(sha256sum "$saved" | cut -d ' ' -f1)"
[ "$before" = "$after" ] || { echo "U1_FAIL // future file rewritten"; exit 1; }
echo "U1_PASS // NATIVE_ATOMIC_PERSISTENCE_RESTART_AND_REFUSAL"
