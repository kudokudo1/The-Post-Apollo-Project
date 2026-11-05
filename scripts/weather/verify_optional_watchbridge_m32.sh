#!/usr/bin/env bash
set -euo pipefail
# Disposable Fedora Quickshell proof. Never installs/launches Stage Director.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
for x in quickshell Xvfb timeout; do
  command -v "$x" >/dev/null || { echo "M32_FAIL // missing $x" >&2; exit 2; }
done
work="$(mktemp -d /tmp/weather-m32-watch.XXXXXXXX)"
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
cp -a "$repo/services/." "$work/config/services/"
Xvfb :94 -screen 0 1300x920x24 -nolisten tcp >"$work/xvfb.log" 2>&1 &
xpid="$!"
export DISPLAY=:94 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.5
kill -0 "$xpid" || { cat "$work/xvfb.log" >&2; exit 1; }

case_run() {
  local name="$1" fixture="$2" marker="$3" rc=0
  cp "$repo/tests/weather/fixtures/$fixture" "$work/config/shell.qml"
  echo "M32_CASE // $name"
  timeout --signal=TERM --kill-after=3s 24s \
    env -u WAYLAND_DISPLAY \
    HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-home" \
    XDG_CACHE_HOME="$work/cache" QT_LOGGING_RULES="qml.debug=true" \
    QML_IMPORT_PATH="$work/config/qml" \
    quickshell --no-color --log-rules "qml.debug=true" \
      -p "$work/config/shell.qml" >"$work/$name.log" 2>&1 || rc="$?"
  cat "$work/$name.log"
  if [ "$rc" -ne 0 ] || ! grep -Fq "$marker" "$work/$name.log" || \
     grep -Eq 'M32_FAIL|ReferenceError:|TypeError:|Failed to load configuration|module "PostApollo.StageDirector" is not installed' "$work/$name.log"; then
    echo "M32_FAIL // $name rc=$rc" >&2
    exit 1
  fi
}

# No QML module search dir exists yet. A default-off Weather gate MUST boot.
case_run absent M32WatchNoModule.qml \
  "M32_PASS // OPTIONAL_NATIVE_PLUGIN_ABSENT_DEFAULT_OFF"
mkdir -p "$work/config/qml/PostApollo/StageDirector"
cp "$repo/tests/weather/fixtures/M32StageDirectorStub/qmldir" \
  "$work/config/qml/PostApollo/StageDirector/qmldir"
cp "$repo/tests/weather/fixtures/M32StageDirectorStub/WatchBridge.qml" \
  "$work/config/qml/PostApollo/StageDirector/WatchBridge.qml"
# Fake plugin only simulates lifecycle for QML. SwayPX CI tests REAL peer.
case_run mock M32WatchWithStub.qml \
  "M32_PASS // REAL_QML_GATE_AND_MEDIA"
echo "M32_NATIVE_OPTIONAL_WATCH: no_plugin_default=PASS mock_watch_close=PASS "
echo "M32_NO_NATIVE_BROWSER_OR_KITTY=PASS"
