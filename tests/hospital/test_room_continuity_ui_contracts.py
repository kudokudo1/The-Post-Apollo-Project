#!/usr/bin/env python3
"""Room outlives Doctor: verify pure read-only scope and durable UI route."""
from pathlib import Path

base = Path(__file__).resolve().parents[2]
reader = (base / "services/hospital/HospitalRoomContinuityService.qml").read_text()
policy = (base / "services/hospital/HospitalRoomContinuityPolicy.js").read_text()
panel = (base / "widgets/HospitalRoomContinuityView.qml").read_text()
worker = (base / "widgets/HospitalRegisteredWorkerView.qml").read_text()
hospital = (base / "widgets/HospitalW.qml").read_text()
issues = []


def require(v, reason):
    if not v:
        issues.append(reason)


require('property string roomId: ""' in reader and 'property bool enabled: false' in reader,
        "Reader must require explicit Room and visible mode")
require('readonly property var stages:' in reader
        and '"room", "assignments", "checkpoints", "reports"' in reader
        and '"roomChart", "patientChart"' in reader,
        "Continuity must use existing Room/Assignment/Checkpoint/Report/Chart records")
require('const id = String(root.roomId || "").trim()' in reader
        and 'id !== root.requestedRoomId' in reader,
        "Async reads must remain pinned to the Room requested")
require('if (!root.enabled || id !== root.requestedRoomId)' in reader,
        "Stale results must never be rendered for another Room")
require('snapshot = ({})' in reader and 'loaded = false;' in reader,
        "Changing or closing a Room must clear visible saved data")
require('root.scheduleRefresh();' in reader
        and 'if (root.refreshScheduled)' in reader,
        "Mode activation must coalesce duplicate PX reads")
require('if (reader.running || root.loading)' in reader,
        "Only one PX read should be in flight")
require('root.snapshot = root.pendingSnapshot' in reader,
        "Publish only a verified complete snapshot, not partially mixed data")
require('String(payload.id || "") !== id' in reader,
        "Room response must match the pinned Room")
require('String(row.roomId || "") !== id' in reader,
        "Assignments, reports, checkpoint and Room Chart must match the Room")
require('String(row.patientId || "") !== patientId' in reader,
        "Patient Chart must be scoped to the Room Patient")
require('String(row.status || "") !== "ACTIVE"' in reader,
        "Only ACTIVE Chart entries should be presented")
require('"hospital", "room", id' in reader
        and '"hospital", "assignments", "--room-id", id' in reader
        and '"hospital", "checkpoints", id' in reader
        and '"hospital", "room-reports", id' in reader
        and '"hospital", "chart-entries", "--scope", "ROOM"' in reader
        and '"hospital", "chart-entries", "--scope", "PATIENT"' in reader,
        "Use existing scoped PX read commands; no new store is justified")
for mutating in ('"room-bind"', '"session-put"', '"session-create"',
                 '"room-report-append"', '"checkpoint-append"',
                 '"chart-entry-add"', '"agent"', '"turn"'):
    require(mutating not in reader, "Continuity reader cannot write/launch " + mutating)

require('function project(args)' in policy and 'function checklist(markdown)' in policy,
        "Render deterministic summary from actual durable records")
require('NO PARSEABLE CHECKLIST // NO PROGRESS MEASUREMENT' in policy,
        "Missing checklist must never imply zero percent completion")
require('COUNTED CHECKBOXES // NOT VERIFIED COMPLETION' in policy,
        "Checkbox progress must not claim technical verification")
require('SESSION DATA UNVERIFIED' in policy
        and 'ROOM PERSISTS' in policy
        and 'SESSION OWNERSHIP COLLISION' in policy,
        "Room must remain readable without a live Session; uncertainty visible")
require('upper((v || {}).kind) === "HANDOFF"' in policy,
        "Find latest HANDOFF separately from latest ordinary report")
require('str(v.authorRole).toLowerCase() === "operator"' in policy,
        "Distinguish approved decisions from Doctor suggestions")
require('str(v.id) === assignmentId' in policy,
        "Assignment must be selected from saved Room binding, not guessed")
require('NO PROVIDER HEARTBEAT OR AUTOMATIC RECOVERY' in policy,
        "Do not claim seamless recovery or live connectivity")

require('HospitalRoomContinuityService {' in panel
        and 'enabled: root.active && root.roomId.length > 0' in panel,
        "Only load durable Room details when user opens the panel")
require('text: "PERMANENT ROOM // CONTINUITY"' in panel
        and 'text: "CURRENT ASSIGNMENT"' in panel
        and 'text: "LAST CHECKPOINT // "' in panel
        and 'text: "LAST HANDOFF // "' in panel
        and 'text: "NEXT RECORDED INPUT // "' in panel,
        "Show work, recent evidence, handoff, and next saved action without opening chat")
require('root.overview.progress.percent || 0' in panel
        and 'root.overview.progress.total' in panel,
        "Visual progress must be based on actual checklist")
require('NeonScrollBar {' in panel and 'flickable: contentScroll' in panel,
        "Dense briefing should scroll with existing visual language")
require('root.overview.recovery.label' in panel
        and 'no browser ChatGPT recovery' in panel,
        "Recovery state is conservative and visibly scoped")

require('label: "ROOM // STATUS"' in worker
        and 'selectedAction: root.viewMode === "continuity"' in worker,
        "Permanent Room gets its own main mode")
require('HospitalRoomContinuityView {' in worker
        and 'active: root.active && root.viewMode === "continuity"' in worker
        and 'roomId: active ? root.pinnedRoomId : ""' in worker,
        "Continuity panel uses exact Room ID and lazily loads")
require('initialMode === "chat" ? "chat" : "continuity"' in worker,
        "Room continuity is the default when entering a worker without explicit mode")
require('label: "CHAT // SAVED"' in worker
        and 'label: "QUICK // PX"' in worker
        and 'label: "CONNECTIONS"' in worker,
        "Existing transcript, quick, and connection modes remain accessible")
require('SessionPolicy.canIssueQuick(' in worker
        and 'ConnectionPolicy.allowsCommand(' in worker,
        "New read-only mode does not bypass Quick safety gates")
require('label: "ROOM"' in hospital
        and 'rosterRow.rosterData, "continuity"' in hospital,
        "Every registered worker card should expose direct Room briefing")
require('root.rosterFocusedMode = modeValue === "connections"' in hospital
        and 'modeValue === "chat" ? "chat"' in hospital
        and 'modeValue === "attachPreview" ? "attachPreview" : "continuity"' in hospital,
        "Direct worker routes preserve explicit mode choices and safe attachment preview")

if issues:
    print("HOSPITAL ROOM CONTINUITY UI // FAIL")
    for issue in issues:
        print(" -", issue)
    raise SystemExit(1)
print("HOSPITAL ROOM CONTINUITY UI // PASS // scoped records, no auto-dispatch, persistent Room and honest progress")
