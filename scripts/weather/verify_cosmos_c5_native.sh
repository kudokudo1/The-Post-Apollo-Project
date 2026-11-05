#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
command -v quickshell >/dev/null || { echo "C5_NATIVE_FAIL // NO_QUICKSHELL"; exit 2; }
work="$(mktemp -d /tmp/cosmos-c5-native.XXXXXXXX)"
trap 'rm -rf -- "$work"' EXIT
mkdir -m 700 "$work/home" "$work/runtime" "$work/cache" "$work/config"
chmod 700 "$work/runtime"
rc=0
timeout --signal=TERM --kill-after=3s 20s env \
  HOME="$work/home" \
  XDG_RUNTIME_DIR="$work/runtime" \
  XDG_CACHE_HOME="$work/cache" \
  XDG_CONFIG_HOME="$work/config" \
  QT_QPA_PLATFORM=offscreen \
  quickshell --no-color -p "$repo_root/tests/weather/fixtures/C5FocusedNativeShell.qml" \
  >"$work/boot.log" 2>&1 || rc=$?
cat "$work/boot.log"
if [ "$rc" -ne 0 ] \
   || ! grep -F "C5_NATIVE_PASS // MODES_LOAD_WITHOUT_SOURCES" "$work/boot.log" >/dev/null \
   || grep -F "C5_NATIVE_FAIL" "$work/boot.log" >/dev/null \
   || grep -F "Failed to load configuration" "$work/boot.log" >/dev/null; then
   echo "C5_NATIVE_FAIL // process_exit=$rc" >&2
   exit 1
fi
echo "C5_NATIVE_PASS // ISOLATED_QML_LOADING_AND_SOURCE_STATUSES"
