#!/usr/bin/env bash
set -euo pipefail
# CI-only native click on the real TOOLS selector and launch ActionButtons.
# Signals are intercepted by the disposable fixture. Zero Kitty/Sway calls.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for name in quickshell Xvfb xdotool node timeout; do
  command -v "$name" >/dev/null || {
    echo "M28C_FAIL // missing $name" >&2
    exit 2
  }
done
work="$(mktemp -d /tmp/weather-m28c-tools.XXXXXXXX)"
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
cp "$repo/tests/weather/fixtures/M28CToolsTerminalControls.qml" \
   "$work/config/shell.qml"

Xvfb :99 -screen 0 1500x1000x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }

log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 25s \
  env -u WAYLAND_DISPLAY \
  HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
  quickshell --no-color --log-rules "qml.debug=true" \
    -p "$work/config/shell.qml" >"$log" 2>&1 &
pid="$!"

wait_for() {
  local marker="$1"
  for ((i=0;i<170;i++)); do
    grep -F "$marker" "$log" >/dev/null 2>&1 && return 0
    if grep -F "M28C_FAIL" "$log" >/dev/null 2>&1 ||
       ! kill -0 "$pid" 2>/dev/null; then
      cat "$log"
      echo "M28C_FAIL // exited before $marker" >&2
      return 1
    fi
    sleep 0.1
  done
  cat "$log"
  echo "M28C_FAIL // timeout waiting for $marker" >&2
  return 1
}
click_at() {
  local name="$1" p x y
  p="$(grep -F "M28C_"$name"_READY // x=" "$log" |
    tail -n 1 | sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
  [ -n "$p" ] || { echo "M28C_FAIL // missing $name point" >&2; exit 1; }
  read -r x y <<<"$p"
  xdotool mousemove --window "$wid" "$x" "$y" click 1
}
wait_for "M28C_NEWS_READY // x="
wid="$(xdotool search --onlyvisible --name 'M28C-TOOLS-TERMINAL-CONTROLS' | head -n 1)"
[ -n "$wid" ] || { cat "$log"; exit 1; }
xdotool windowmove "$wid" 0 0
click_at NEWS
wait_for "M28C_CONSOLE_READY // x="
click_at CONSOLE
wait_for "M28C_PASS // NEWS_CONTEXT_SIGNAL_NO_KITTY"
wait_for "M28C_STAR_READY // x="
click_at STAR
wait_for "M28C_PASS // STAR_MAP_SIGNAL_NO_KITTY"

set +e
wait "$pid"
rc="$?"
set -e
pid=""
cat "$log"
[ "$rc" -eq 0 ] || { echo "M28C_FAIL // Quickshell exit $rc" >&2; exit 1; }
[ -z "$(find "$work/data" -type f -print -quit)" ] ||
  { echo "M28C_FAIL // unexpected disk write in view-only control fixture"; exit 1; }
echo "M28C_PASS // NATIVE_TOOLS_CONTROLS_EMIT_EXACT_SINGLE_LAUNCH_REQUESTS"
