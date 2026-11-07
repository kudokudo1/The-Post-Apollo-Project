#!/usr/bin/env python3
"""Hospital recorded-worker attention UI, explicit source and no fake heartbeat."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
host = (root / "widgets/HospitalW.qml").read_text(encoding="utf-8")
view = (root / "widgets/HospitalRegisteredWorkerView.qml").read_text(
    encoding="utf-8"
)
roster = (root / "services/hospital/HospitalWorkforceRosterPolicy.js").read_text(
    encoding="utf-8"
)
policy = (root / "services/hospital/HospitalWorkerAttentionPolicy.js").read_text(
    encoding="utf-8"
)
responsibility = (root / "services/hospital/HospitalResponsibilityService.qml").read_text(
    encoding="utf-8"
)
issues = []


def require(test, reason):
    if not test:
        issues.append(reason)


require("WorkerAttentionPolicy.describe(rosterData)" in host,
        "Worker card must interpret its exact registered Room")
require('id: attentionStrip' in host,
        "Worker card must expose a visible attention strip")
require('rosterRow.attention.label' in host
        and 'rosterRow.attention.reason' in host,
        "Strip must display the reason, not a decorative status alone")
require('root.openRosterSession(' in host
        and 'rosterRow.rosterData, "quick"' in host,
        "Clicking attention must open its registered Room inspector")
require("workforceAttentionCount" in host
        and "WorkerAttentionPolicy.countAttention(" in host,
        "Operator needs Hospital-level attention count")
require('id: workforceRecordPoll' in host
        and 'interval: 30000' in host
        and 'root.menuOpen && root.workforceRosterVisible' in host
        and 'root.operationsSurface === ""' in host
        and 'root.rosterEditingRoomId.length === 0' in host,
        "Read-only 30s refresh only while WORKERS list is visible and not editing")
require('!responsibilityService.graphLoading' in host
        and 'responsibilityService.refreshDurableGraph();' in host,
        "Refresh must use existing PX registry reads and avoid overlapping processes")
require('responsibilityService.graphError.length > 0' in host
        and 'DISPLAY MAY BE STALE' in host,
        "Registry refresh errors must be shown even when old worker rows remain")
require('text: "REC // " + rosterRow.sessionState' in host,
        "Persisted status must remain explicitly recorded, not falsely live")
require('root.workforceRosterVisible ? [] : auditService.rooms' in host,
        "Do not remove legacy Git branch view")
require('root.openRosterSession(rosterRow.rosterData, "chat")' in host,
        "Do not remove direct Room transcript")
require('root.openRosterSession(rosterRow.rosterData, "quick")' in host,
        "Do not remove exact Session Quick")
require('root.rosterFocusedSessionId = String(current.sessionId || "")' in host,
        "No attention strip may replace exact pinned Session routing")
require('readonly property var recordedAttention:' in view
        and 'WorkerAttentionPolicy.describe(root.roomData)' in view,
        "Inspector must show alert reason from the same Room snapshot")
require("root.recordedAttention.reason" in view
        and "root.recordedAttention.recordedAt" in view,
        "Inspector must show source detail and recorded timestamp")
require("sessionLastError" in roster and "sessionLastExitCode" in roster
        and "sessionEndedAt" in roster,
        "Evidence must come from PX saved Session fields")
require("sessionStatus: rawStatus" in roster
        and "statusRecordedAt:" in roster,
        "Original source status and time must be preserved")
require('hospital sessions --json' in responsibility,
        "Attention board must read PX Session records")
require('"FROZEN"' not in policy and '"ESCALATION"' not in policy,
        "No fabricated frozen or escalation claims")
require('heartbeat not verified' in policy,
        "Recorded OPERATING status must not be called live heartbeat")
require('source: "PX SESSION RECORD"' in policy,
        "Indicators must state their evidence provenance")
require('result.requiresReview = true;' in policy,
        "Review requires an explicit recorded REVIEW state")
require('sessionLastError' in policy and 'sessionLastExitCode' in policy,
        "Failure reasons must rely on recorded error/exit evidence")
require('if (status === "COMPLETE" || status === "ENDED")' in policy,
        "Terminal sessions must not be treated as active attention")

if issues:
    print("HOSPITAL RECORDED WORKER ATTENTION UI // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL RECORDED WORKER ATTENTION UI // PASS")
