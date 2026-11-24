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
    FinanceResearchEvidenceCandidatePreviewHost.qml \
    FinanceResearchInvestigationsPane.qml; do
  cp "$repo_root/widgets/$file" "$work/config/widgets/$file"
done
for service in FinanceResearchCandidatePreviewService.qml \
    FinanceResearchCandidateDraftService.qml \
    FinanceResearchScratchEvidenceService.qml \
    FinanceResearchInvestigationReadService.qml; do
  cp "$repo_root/services/finance/$service" \
    "$work/config/services/finance/"
done
for file in research_candidate_preview_bridge.mjs \
    research_candidate_draft_preview.mjs \
    research_scratch_citation_preview.mjs \
    research_investigation_read_bridge.mjs \
    research_investigation_store.mjs \
    research_evidence_candidates.mjs research_investigations.mjs; do
  cp "$repo_root/scripts/finance/$file" "$work/config/scripts/finance/$file"
done

# M9 uses one synthetic existing case in PRIVATE disposable XDG data. No
# application writer is invoked. The source must remain byte-identical.
case_dir="$work/data/post-apollo/finance/research-investigations"
install -d -m 700 "$case_dir"
cp "$repo_root/tests/finance/fixtures/M9SyntheticInvestigations.json" \
  "$case_dir/investigations.json"
chmod 600 "$case_dir/investigations.json"
cp "$case_dir/investigations.json" "$work/original-case.json"

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
    QT_LOGGING_RULES="qml.debug=true" \
    quickshell --no-color --log-rules "qml.debug=true" \
      -p "$work/config/shell.qml" \
    >"$log" 2>&1 || rc=$?
cat "$log"
if [ "$rc" -ne 0 ] \
    || grep -F 'M7_NATIVE_FAIL //' "$log" >/dev/null; then
  echo "M7_NATIVE_FAIL // process rc=$rc" >&2
  exit 1
fi
if ! grep -F 'M7_NATIVE_CHECK // CANDIDATES_FROM_NODE_VALIDATED' "$log"     || ! grep -F 'M7_NATIVE_PASS // QML_TYPES_AND_READ_ONLY_IPC' "$log"; then
  echo "M7_NATIVE_FAIL // native stage markers absent" >&2
  exit 1
fi
grep -F 'M9_NATIVE_CHECK // EXISTING_CASE_EDITOR_PREFILLED_UNSAVED' "$log"
case_hash="$(sha256sum "$case_dir/investigations.json")"
original_hash="$(sha256sum "$work/original-case.json")"
if [ "${case_hash%% *}" != "${original_hash%% *}" ]; then
  echo "M9_NATIVE_FAIL // synthetic case changed" >&2
  exit 1
fi
if find "$case_dir" -type f -name 'investigations.lock' | grep . >/dev/null; then
  echo "M9_NATIVE_FAIL // write lock created" >&2
  exit 1
fi
echo "M7_NATIVE_PASS // NO_USER_STORAGE_OR_PROVIDER"
echo "M9_NATIVE_PASS // UNSAVED_CASE_DRAFT_NO_WRITES"
