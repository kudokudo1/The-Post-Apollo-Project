#!/usr/bin/env bash
set -euo pipefail
# M28-B CI-only: actual Quickshell NEWS source/list/viewer and native click.
# Fake GDELT-style rows, no external network or workstation mutation.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool timeout; do
  command -v "$cmd" >/dev/null || { echo "M28B_FAIL // missing $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/weather-m28b-news.XXXXXXXX)"
pid="" xpid=""
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
cp "$repo/tests/weather/fixtures/M28BNewsFeedFirst.qml" "$work/config/shell.qml"
# Substitute the existing service only inside the disposable CI copy.
cp "$repo/tests/weather/fixtures/M28BStationDiscoveryService.qml" \
   "$work/config/services/weather/StationDiscoveryService.qml"

Xvfb :99 -screen 0 1200x1000x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }
log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 29s \
  env -u WAYLAND_DISPLAY \
  HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
  quickshell --no-color --log-rules "qml.debug=true" \
  -p "$work/config/shell.qml" >"$log" 2>&1 &
pid="$!"
wait_for() {
  local needle="$1"
  for ((i=0;i<185;i++)); do
    grep -F "$needle" "$log" >/dev/null 2>&1 && return 0
    if grep -F "M28B_FAIL" "$log" >/dev/null 2>&1 ||
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"
      echo "M28B_FAIL // exited before $needle" >&2
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "M28B_FAIL // timeout waiting for $needle" >&2
  return 1
}
wait_for "M28B_NEWS_CARD_READY // x="
wid="$(xdotool search --onlyvisible --name 'M28B-NEWS-FEED-FIRST' | head -n1)"
[ -n "$wid" ] || { cat "$log"; echo "M28B_FAIL // no test window"; exit 1; }
xdotool windowmove "$wid" 0 0
coords="$(grep -F 'M28B_NEWS_CARD_READY // x=' "$log" | tail -n 1 |
  sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
read -r x y <<<"$coords"
[ -n "$x" ] && [ -n "$y" ] || { echo "M28B_FAIL // no card coords"; exit 1; }
xdotool mousemove --window "$wid" "$x" "$y" click 1
wait_for "M28B_PASS // REAL_NEWS_FEED_FIRST_WITH_INDEPENDENT_ANALYTICS"
set +e
wait "$pid"
rc="$?"
set -e
pid=""
cat "$log"
[ "$rc" -eq 0 ] || { echo "M28B_FAIL // Quickshell rc=$rc"; exit 1; }
grep -F 'M28B_PASS // NATIVE_HEADLINE_CARD_OPENS_VIEWER' "$log" >/dev/null
grep -F 'M28B_PASS // TRENDS_IN_DEDICATED_SUBJECT_ROUTE' "$log" >/dev/null
for filename in weather-dossier-archive-v1.json weather-event-archive-v1.json; do
  [ -z "$(find "$work/data" -name "$filename" -print -quit)" ] || {
    echo "M28B_FAIL // unexpected archive file $filename"; exit 1;
  }
done
echo 'M28B_PASS // FEDORA_NATIVE_NEWS_FEED_AND_VIEWER'
