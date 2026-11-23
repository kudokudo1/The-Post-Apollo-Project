#!/usr/bin/env bash
set -euo pipefail

# Research M7: disposable Quickshell/Xvfb QML startup and local-only IPC test.
# NEVER install into the operator's home or call a live SEC/Crawl provider.
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
for command in quickshell node timeout Xvfb; do
  command -v "$command" >/dev/null || {
    echo "M7_NATIVE_FAIL // missing $command" >&2
    exit 2
  }
done

work="$(mktemp -d /tmp/research-m7-native.XXXXXXXX)"
xvfb_pid=""
cleanup() {
  [ -z "$xvfb_pid" ] || kill "$xvfb_pid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT

install -d -m 700 "$work/home" "$work/run" "$work/data" \
  "$work/cache" "$work/config-root" "$work/config/widgets" \
  "$work/config/services/finance" "$work/config/scripts/finance"
cp "$repo_root/tests/finance/fixtures/M7ResearchCandidateNativeShell.qml" \
  "$work/config/shell.qml"
cp -a "$repo_root/components" "$work/config/components"
for file in FinanceResearchEvidenceCandidatePicker.qml \
    FinanceResearchEvidenceCandidatePreviewHost.qml; do
  cp "$repo_root/widgets/$file" "$work/config/widgets/$file"
done
cp "$repo_root/services/finance/FinanceResearchCandidatePreviewService.qml" \
  "$work/config/services/finance/"
for file in research_candidate_preview_bridge.mjs \
    research_evidence_candidates.mjs research_investigations.mjs; do
  cp "$repo_root/scripts/finance/$file" "$work/config/scripts/finance/$file"
done

Xvfb :98 -screen 0 1280x1024x24 -nolisten tcp \
  >"$work/xvfb.log" 2>&1 &
xvfb_pid="$!"
export DISPLAY=:98
export QT_QPA_PLATFORM=xcb
export QT_QUICK_BACKEND=software
sleep 0.4
if ! kill -0 "$xvfb_pid" 2>/dev/null; then
  cat "$work/xvfb.log"
  echo "M7_NATIVE_FAIL // virtual display unavailable" >&2
  exit 1
fi

log="$work/quickshell.log"
rc=0
timeout --signal=TERM --kill-after=3s 27s \
  env -u WAYLAND_DISPLAY \
    HOME="$work/home" \
    XDG_RUNTIME_DIR="$work/run" \
    XDG_DATA_HOME="$work/data" \
    XDG_CONFIG_HOME="$work/config-root" \
    XDG_CACHE_HOME="$work/cache" \
    quickshell --no-color -p "$work/config/shell.qml" \
    >"$log" 2>&1 || rc=$?
cat "$log"
if [ "$rc" -ne 0 ] \
    || grep -F 'M7_NATIVE_FAIL //' "$log" >/dev/null; then
  echo "M7_NATIVE_FAIL // process rc=$rc" >&2
  exit 1
fi
grep -F 'M7_NATIVE_CHECK // CANDIDATES_FROM_NODE_VALIDATED' "$log"
grep -F 'M7_NATIVE_PASS // QML_TYPES_AND_READ_ONLY_IPC' "$log"
if find "$work/data" -type f \
    \( -name 'investigations.json' -o -name 'investigations.lock' \) \
    | grep . >/dev/null; then
  echo "M7_NATIVE_FAIL // research storage was touched" >&2
  exit 1
fi
echo "M7_NATIVE_PASS // NO_USER_STORAGE_OR_PROVIDER"
