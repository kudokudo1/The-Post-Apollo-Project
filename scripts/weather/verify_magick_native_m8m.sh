#!/usr/bin/env bash
set -euo pipefail
# Real Qt/Quickshell in disposable private XDG roots. NO live desktop touch.
repo="$(cd "$(dirname "$0")/../.." && pwd)"
qs="$(command -v quickshell || true)"
if [ -z "$qs" ]; then
  echo "M8M_NATIVE_FAIL // quickshell absent" >&2
  exit 2
fi
work="$(mktemp -d /tmp/magick-m8m-native.XXXXXXXX)"
trap 'rm -rf -- "$work"' EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" "$work/cache" \
   "$work/config-root" "$work/config/widgets" "$work/config/services" \
   "$work/config/qs/services"
cp -a "$repo/components" "$work/config/components"
cp -a "$repo/widgets/weather" "$work/config/widgets/weather"
cp -a "$repo/widgets/tasks" "$work/config/widgets/tasks"
cp -a "$repo/services/weather" "$work/config/services/weather"
cp -a "$repo/services/location" "$work/config/services/location"
cp -a "$repo/services/location" "$work/config/qs/services/location"
cp "$repo/tests/weather/fixtures/M8mNativeMatrixVisualShell.qml" \
   "$work/config/shell.qml"
rc=0
timeout --signal=TERM --kill-after=3s 25s \
  env -u DISPLAY -u WAYLAND_DISPLAY \
  HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
  XDG_DATA_HOME="$work/data" XDG_CONFIG_HOME="$work/config-root" \
  XDG_CACHE_HOME="$work/cache" QML_IMPORT_PATH="$work/config" \
  QT_QPA_PLATFORM=offscreen \
  "$qs" --no-color -p "$work/config/shell.qml" \
  > "$work/native.log" 2>&1 || rc=$?
cat "$work/native.log"
if [ "$rc" -ne 0 ] || \
   ! grep -F "M8M_NATIVE_PASS // SOURCE_HEATMAP_TIMELINE_INSPECTOR_AND_WHEEL" \
       "$work/native.log" >/dev/null || \
   grep -F "M8M_NATIVE_FAIL" "$work/native.log" >/dev/null; then
  echo "M8M_NATIVE_FAIL // offscreen QML rc=$rc" >&2
  exit 1
fi
if find "$work/data" -type f \( -iname '*natal*' -o \
    -iname '*transit*' -o -iname '*event*' \) | grep .; then
  echo "M8M_NATIVE_FAIL // unexpected private chart storage" >&2
  exit 1
fi
echo "M8M_NATIVE_PASS // NO_REAL_DESKTOP_FILES_CHANGED"
