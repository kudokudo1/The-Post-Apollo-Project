#!/usr/bin/env bash
set -euo pipefail
# M9a: genuine Quickshell test in disposable Xvfb with an EMPTY Research store.
# This is CI-only; do not modify operator's ~/.config/quickshell or XDG_DATA.
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
for command in quickshell node timeout Xvfb sha256sum; do
  command -v "$command" >/dev/null || {
    echo "M9A_NATIVE_FAIL // missing $command" >&2
    exit 2
  }
done

work="$(mktemp -d /tmp/research-m9a-scratch.XXXXXXXX)"
xvfb_pid=""
cleanup() {
  [ -z "$xvfb_pid" ] || kill "$xvfb_pid" 2>/dev/null || true
  rm -rf -- "$work"
}
trap cleanup EXIT

install -d -m 700 "$work/home" "$work/run" "$work/data" \
  "$work/cache" "$work/config-root" "$work/config/widgets" \
  "$work/config/services/finance" "$work/config/scripts/finance"
cp "$repo_root/tests/finance/fixtures/M9aResearchScratchNativeShell.qml" \
  "$work/config/shell.qml"
cp -a "$repo_root/components" "$work/config/components"
for file in FinanceResearchEvidenceCandidatePicker.qml \
  FinanceResearchEvidenceCandidatePreviewHost.qml \
  FinanceResearchInvestigationsPane.qml; do
  cp "$repo_root/widgets/$file" "$work/config/widgets/$file"
done
for file in FinanceResearchCandidatePreviewService.qml \
  FinanceResearchCandidateDraftService.qml \
  FinanceResearchScratchEvidenceService.qml \
  FinanceResearchInvestigationReadService.qml; do
  cp "$repo_root/services/finance/$file" \
    "$work/config/services/finance/$file"
done
for file in research_candidate_preview_bridge.mjs \
  research_candidate_draft_preview.mjs \
  research_scratch_citation_preview.mjs \
  research_investigation_read_bridge.mjs \
  research_investigation_store.mjs \
  research_evidence_candidates.mjs \
  research_investigations.mjs; do
  cp "$repo_root/scripts/finance/$file" "$work/config/scripts/finance/$file"
done

# No investigations.json is created. Any file is a forbidden write.
Xvfb :97 -screen 0 1280x1024x24 -nolisten tcp \
  >"$work/xvfb.log" 2>&1 &
xvfb_pid="$!"
export DISPLAY=:97 QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
sleep 0.4
if ! kill -0 "$xvfb_pid" 2>/dev/null; then
  cat "$work/xvfb.log"
  echo "M9A_NATIVE_FAIL // virtual display unavailable" >&2
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
      -p "$work/config/shell.qml" >"$log" 2>&1 || rc=$?
cat "$log"
if [ "$rc" -ne 0 ] || grep -F 'M9A_NATIVE_FAIL //' "$log" >/dev/null; then
  echo "M9A_NATIVE_FAIL // process rc=$rc" >&2
  exit 1
fi
for marker in \
  'M9A_NATIVE_CHECK // CASE_CREATED_WITH_NO_STORED_CASES' \
  'M9A_NATIVE_CHECK // UNSAVED_SEC_CITATION_PREFILLED' \
  'M9A_NATIVE_CHECK // SCRATCH_DISCARD_CLEARED' \
  'M9A_NATIVE_CHECK // SOURCE_CHANGE_DISCARDED_SCRATCH' \
  'M9A_NATIVE_PASS // EMPTY_STORE_SCRATCH_AND_DRAFT'; do
  if ! grep -F "$marker" "$log"; then
    echo "M9A_NATIVE_FAIL // missing marker: $marker" >&2
    exit 1
  fi
done
if find "$work/data" -type f | grep . >/dev/null; then
  echo "M9A_NATIVE_FAIL // any Research file created in empty store" >&2
  exit 1
fi
echo "M9A_NATIVE_PASS // ZERO_LOCAL_WRITES"
