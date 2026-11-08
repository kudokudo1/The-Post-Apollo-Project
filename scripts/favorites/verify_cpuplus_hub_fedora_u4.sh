#!/usr/bin/env bash
set -euo pipefail
# CI-only native CPU++ Favorites pane with synthetic owners.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for cmd in quickshell Xvfb xdotool timeout; do
  command -v "$cmd" >/dev/null ||
    { echo "U4_FAIL // missing executable: $cmd"; exit 2; }
done
work="$(mktemp -d /tmp/cpu-favorites.XXXXXXXX)"
pid=""
xpid=""
cleanup() {
  [ -z "$pid" ] || kill "$pid" 2>/dev/null || true
  [ -z "$xpid" ] || kill "$xpid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" \
  "$work/cache" "$work/config-home" "$work/config/widgets/cpuplus" \
  "$work/config/services/favorites" "$work/config/widgets/appcontrol" \
  "$work/config/services/weather"
cp -a "$repo/components" "$work/config/components"
cp "$repo/widgets/cpuplus/CpuPlusFavoritesHubPane.qml" \
  "$work/config/widgets/cpuplus/"
cp "$repo/widgets/appcontrol/AppControlFavoriteDisplaySource.qml" \
  "$work/config/widgets/appcontrol/"
cp "$repo/services/favorites/"* "$work/config/services/favorites/"
cp "$repo/services/weather/WeatherHomeFavoritesPolicy.js" \
  "$work/config/services/weather/"
cp "$repo/tests/cpuplus/fixtures/CpuPlusFavoritesNative.qml" \
  "$work/config/shell.qml"

Xvfb :99 -screen 0 1200x800x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:99 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.4
kill -0 "$xpid" || { cat "$work/xvfb.log"; exit 1; }
log="$work/quickshell.log"
timeout --signal=TERM --kill-after=3s 22s \
  env -u WAYLAND_DISPLAY HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
  XDG_CACHE_HOME="$work/cache" \
  quickshell --no-color --log-rules "qml.debug=true" \
    -p "$work/config/shell.qml" >"$log" 2>&1 &
pid="$!"
for ((i=0;i<100;i++)); do
  if grep -F "U4_FAIL" "$log" >/dev/null; then
    cat "$log"; echo "U4_FAIL // QML fixture"; exit 1
  fi
  if grep -F "U4_READY // x=" "$log" >/dev/null; then
    break
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    cat "$log"; echo "U4_FAIL // process exited without UI"; exit 1
  fi
  sleep 0.1
done
grep -F "U4_READY // x=" "$log" >/dev/null ||
  { cat "$log"; echo "U4_FAIL // no ready marker"; exit 1; }
window="$(xdotool search --onlyvisible --name 'CPU-FAVORITES-NATIVE' | head -n 1)"
[ -n "$window" ] ||
  { cat "$log"; echo "U4_FAIL // no visible window"; exit 1; }
xdotool windowmove "$window" 0 0
coords="$(grep -F 'U4_READY // x=' "$log" | tail -n 1 |
  sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
read -r x y <<<"$coords"
[ -n "$x" ] && [ -n "$y" ] ||
  { cat "$log"; echo "U4_FAIL // no click coordinates"; exit 1; }
xdotool mousemove --window "$window" "$x" "$y" click 1
# Then click a real FILES row in the left dossier. This validates the whole
# routing chain: left index -> center category -> selected right-side details.
for ((i=0;i<100;i++)); do
  if grep -F "U4_FAIL" "$log" >/dev/null; then
    cat "$log"; echo "U4_FAIL // native dossier event"; exit 1
  fi
  if grep -F 'U4_SECOND_READY // x=' "$log" >/dev/null; then
    break
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    cat "$log"; echo "U4_FAIL // exited before dossier route"; exit 1
  fi
  sleep 0.1
done
grep -F 'U4_SECOND_READY // x=' "$log" >/dev/null ||
  { cat "$log"; echo "U4_FAIL // no dossier row coordinate"; exit 1; }
second_coords="$(grep -F 'U4_SECOND_READY // x=' "$log" | tail -n 1 |
  sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
read -r ix iy <<<"$second_coords"
[ -n "$ix" ] && [ -n "$iy" ] ||
  { cat "$log"; echo "U4_FAIL // invalid dossier coordinates"; exit 1; }
xdotool mousemove --window "$window" "$ix" "$iy" click 1
# U6b: the QML fixture next verifies prior U6a controls and exposes the
# real left collection heading's mouse coordinates. Click it as a user would.
for ((i=0;i<100;i++)); do
  if grep -F "U4_FAIL" "$log" >/dev/null; then
    cat "$log"; echo "U6B_FAIL // fixture before collection click"; exit 1
  fi
  if grep -F 'U6B_GROUP_READY // x=' "$log" >/dev/null; then
    break
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    cat "$log"; echo "U6B_FAIL // exited before group click"; exit 1
  fi
  sleep 0.1
done
grep -F 'U6B_GROUP_READY // x=' "$log" >/dev/null ||
  { cat "$log"; echo "U6B_FAIL // missing collection heading"; exit 1; }
group_coords="$(grep -F 'U6B_GROUP_READY // x=' "$log" | tail -n 1 |
  sed -E 's/.*x=([0-9]+) y=([0-9]+).*/\1 \2/')"
read -r gx gy <<<"$group_coords"
[ -n "$gx" ] && [ -n "$gy" ] ||
  { cat "$log"; echo "U6B_FAIL // bad group coordinates"; exit 1; }
xdotool mousemove --window "$window" "$gx" "$gy" click 1
set +e
wait "$pid"
rc="$?"
set -e
pid=""
cat "$log"
[ "$rc" -eq 0 ] ||
  { echo "U4_FAIL // process exit $rc"; exit 1; }
if grep -F "U4_FAIL" "$log" >/dev/null; then
  echo "U4_FAIL // failure marker even if success present"; exit 1
fi
grep -F 'U4_PASS // SELECTED_PROCESS_READ_ONLY' "$log" >/dev/null ||
  { echo "U4_FAIL // click did not select row"; exit 1; }
grep -F 'U4_PASS // DOSSIER_FILE_NAVIGATION_READ_ONLY' "$log" >/dev/null ||
  { echo "U4_FAIL // left dossier click did not reach right details"; exit 1; }
grep -F 'U6_PASS // SAFE_MEMBER_ONLY_NO_PROVIDER_WRITES' "$log" >/dev/null ||
  { echo "U6_FAIL // cross-widget collection gate was not verified"; exit 1; }
grep -F 'U6B_PASS // COLLECTION_TO_SELECTOR_AND_DETAILS_NO_WRITES' "$log" >/dev/null ||
  { echo "U6B_FAIL // live left collection click did not route to center"; exit 1; }
if find "$work/data" -type f | grep -q .; then
  echo "U4_FAIL // manager created a writer file"; exit 1
fi
echo "U4_PASS // NATIVE_SELECTOR_NO_DUPLICATE_WRITES"
