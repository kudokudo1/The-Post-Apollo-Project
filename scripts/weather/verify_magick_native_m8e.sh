#!/usr/bin/env bash
set -euo pipefail
# M8e: disposable real Quickshell + Qt scene, never connect to user's desktop.
root="$(cd "$(dirname "$0")/../.." && pwd)"
qs="$(command -v quickshell || true)"
if [[ -z "$qs" ]]; then
  echo "M8E_NATIVE_FAIL // quickshell executable missing" >&2
  exit 2
fi
command -v timeout >/dev/null || exit 2
work="$(mktemp -d /tmp/magick-m8e-native.XXXXXXXX)"
trap 'rm -rf -- "$work"' EXIT
install -d -m 700 "$work/home" "$work/run" "$work/data" "$work/cache" \
    "$work/config-root" "$work/config/widgets" "$work/config/services" \
    "$work/config/qs/services"
cp -a "$root/components" "$work/config/components"
cp -a "$root/widgets/tasks" "$work/config/widgets/tasks"
cp -a "$root/widgets/weather" "$work/config/widgets/weather"
cp -a "$root/services/weather" "$work/config/services/weather"
cp -a "$root/services/location" "$work/config/services/location"
cp -a "$root/services/location" "$work/config/qs/services/location"
cp "$root/tests/weather/fixtures/M8eNativeMagickShell.qml" "$work/config/shell.qml"

# Sandbox QML modules, XDG data and process. The real source HOME and
# ~/.config/quickshell are never referenced, mutated or reloaded.
rc=0
timeout --signal=TERM --kill-after=3s 30s \
  env -u DISPLAY -u WAYLAND_DISPLAY \
    HOME="$work/home" XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" XDG_CACHE_HOME="$work/cache" \
    XDG_CONFIG_HOME="$work/config-root" \
    QML_IMPORT_PATH="$work/config" \
    QT_QPA_PLATFORM=offscreen \
    "$qs" --no-color -p "$work/config/shell.qml" \
    > "$work/native.log" 2>&1 || rc=$?
cat "$work/native.log"
if [[ "$rc" -ne 0 ]] || \
  ! grep -F "M8E_NATIVE_PASS // REAL_QML_DATE_HOME_TRANSIT_COMPONENTS" \
      "$work/native.log" >/dev/null || \
  grep -F "M8E_NATIVE_FAIL" "$work/native.log" >/dev/null; then
  echo "M8E_NATIVE_FAIL // real QML runtime rc=$rc" >&2
  exit 1
fi
if find "$work/data" -type f -name '*natal*' -o -name '*transit*' | grep .; then
  echo "M8E_NATIVE_FAIL // unexpected saved personal chart" >&2
  exit 1
fi
echo "M8E_NATIVE_PASS // ISOLATED_NO_REAL_DESKTOP_CHANGES"
