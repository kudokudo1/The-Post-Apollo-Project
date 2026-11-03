#!/usr/bin/env bash
set -euo pipefail
# CI-only: actual Quickshell ActionButton click, Weather FileView persistence,
# clean process restart, malformed/unsupported byte-preservation refusal.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool node timeout; do
  command -v "$cmd" >/dev/null || { echo "W2B_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/weather-home-favs-w2b.XXXXXXXX)"
pid=""
xpid=""
cleanup(){
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" "$work/cache" \
  "$work/config-home" "$work/config/widgets/weather" "$work/config/services/weather"
cp -a "$repo/components" "$work/config/components"
cp "$repo/widgets/weather/StationHomeMetricCard.qml" "$work/config/widgets/weather/"
cp "$repo/services/weather/WeatherHomeFavoritesStore.qml" \
   "$repo/services/weather/WeatherHomeFavoritesPolicy.js" \
   "$work/config/services/weather/"
cp "$repo/tests/weather/fixtures/M27BHomeFavoritesProbe.qml" "$work/config/shell.qml"

Xvfb :99 -screen 0 1024x768x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.4
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }

wait_for(){
  local marker="$1"
  for ((i=0;i<155;i++)); do
    grep -F "$marker" "$log" >/dev/null 2>&1 && return 0
    if grep -F "W2B_FAIL" "$log" >/dev/null 2>&1 ||
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"
      echo "W2B_FAIL // exited before $marker"
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "W2B_FAIL // timeout waiting for $marker"
  return 1
}
run_phase(){
  local phase="$1" success="$2"
  log="$work/$phase.log"
  echo "W2B_PHASE // $phase"
  timeout --signal=TERM --kill-after=3s 22s \
    env -u WAYLAND_DISPLAY \
    HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
    XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
    W2B_PHASE="$phase" \
    quickshell --no-color --log-rules "qml.debug=true" \
    -p "$work/config/shell.qml" >"$log" 2>&1 &
  pid="$!"
  if [ "$phase" = "save" ]; then
    wait_for "W2B_PIN_READY // x="
    local window coords x y
    window="$(xdotool search --onlyvisible --name "W2B-HOME-FAVORITES" | head -n 1)"
    [ -n "$window" ] || { cat "$log"; echo "W2B_FAIL // missing window"; return 1; }
    xdotool windowmove "$window" 0 0
    coords="$(grep -F 'W2B_PIN_READY // x=' "$log" | tail -n 1 |
      sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
    read -r x y <<<"$coords"
    [ -n "$x" ] && [ -n "$y" ] || { echo "W2B_FAIL // missing coords"; return 1; }
    # Actual native left mouse click on original StationHomeMetricCard pin.
    xdotool mousemove --window "$window" "$x" "$y" click 1
    wait_for "W2B_PIN_CLICK_ACCEPTED"
  fi
  wait_for "$success"
  local rc
  set +e
  wait "$pid"
  rc="$?"
  set -e
  pid=""
  cat "$log"
  [ "$rc" -eq 0 ] || { echo "W2B_FAIL // quickshell $phase rc=$rc"; return 1; }
}

run_phase save "W2B_PASS // NATIVE_PIN_AND_PANEL_FILEVIEW_SAVED"
p="$(find "$work/data" -name weather-home-favorites-v1.json -print -quit)"
[ -n "$p" ] && [ -f "$p" ] || {
  echo "W2B_FAIL // missing saved Weather preferences file"; exit 1;
}
node - "$p" <<'NODE'
const assert=require("node:assert/strict"), fs=require("node:fs");
const d=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
assert.deepEqual(d,{
  schema:"post-apollo.weather-home-favorites.v1",
  version:1,
  revision:2,
  panelRoutes:["home/auto","home/runtime"],
  cardKeys:["sky|next-hours"]
});
console.log("W2B_PASS // EXACT_IDS_ONLY_DISK_RECORD");
NODE
[ -z "$(find "$work/data" -name appcontrol-favorites.json -print -quit)" ] ||
  { echo "W2B_FAIL // AppControl preferences touched"; exit 1; }

run_phase read "W2B_PASS // RESTART_READBACK_IDS_ONLY"
printf '{"schema":' > "$p"
before="$(sha256sum "$p" | cut -d ' ' -f1)"
run_phase corrupt "W2B_PASS // CORRUPT_PRESERVED_AND_REFUSED"
after="$(sha256sum "$p" | cut -d ' ' -f1)"
[ "$before" = "$after" ] || { echo "W2B_FAIL // damaged file was overwritten"; exit 1; }

printf '{"schema":"post-apollo.weather-home-favorites.v1","version":99,"revision":0,"panelRoutes":[],"cardKeys":[]}\n' > "$p"
before="$(sha256sum "$p" | cut -d ' ' -f1)"
run_phase unsupported "W2B_PASS // UNSUPPORTED_PRESERVED_AND_REFUSED"
after="$(sha256sum "$p" | cut -d ' ' -f1)"
[ "$before" = "$after" ] || { echo "W2B_FAIL // unsupported file overwritten"; exit 1; }
echo 'W2B_PASS // NATIVE_FILEVIEW_RESTART_AND_REFUSAL'
