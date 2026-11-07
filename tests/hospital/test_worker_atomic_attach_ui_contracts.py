#!/usr/bin/env python3
"""Hospital staged atomic Session attach wiring. No desktop or PX writes."""
from pathlib import Path

base = Path(__file__).resolve().parents[2]
host = (base / "widgets/HospitalW.qml").read_text(encoding="utf-8")
view = (base / "widgets/HospitalRegisteredWorkerView.qml").read_text(encoding="utf-8")
reader = (base / "services/hospital/HospitalWorkerAttachmentPreviewService.qml").read_text(encoding="utf-8")
actor = (base / "services/hospital/HospitalWorkerAttachmentActionService.qml").read_text(encoding="utf-8")
preview = (base / "services/hospital/HospitalWorkerAttachmentPreviewPolicy.js").read_text(encoding="utf-8")
issues = []


def require(condition, issue):
    if not condition:
        issues.append(issue)


require('HospitalWorkerAttachmentActionService {' in view,
        "Explicit action service only inside registered-worker inspector")
require('id: attachmentAction' in view,
        "Action service identity bound to a single worker view")
require('function armAttachment()' in view
        and 'function confirmAttachment()' in view,
        "Separate REVIEW and CONFIRM operations required")
require('onTriggered: root.armAttachment()' in view,
        "First click only arms local confirmation state")
require('onTriggered: root.confirmAttachment()' in view,
        "Second click explicitly confirms registration")
require('label: "CONFIRM ATTACH // REGISTER IDLE SESSION"' in view,
        "Operator sees state changing action verb")
require('enabledAction: root.attachmentArmed' in view
        and '&& root.attachmentPreview.reviewable' in view,
        "CONFIRM is locked until existing preview passes")
require('attachmentArmKey === attachmentSelectionKey' in view,
        "Changed Room, Session or selection invalidates confirmation")
require('onPreviewAssignmentIdChanged: attachmentArmKey = ""' in view
        and 'onPreviewDoctorIdChanged: attachmentArmKey = ""' in view
        and 'onPreviewProviderIdChanged: attachmentArmKey = ""' in view,
        "Changing any selected participant disarms attachment")
require('onPinnedRoomIdChanged: {' in view
        and 'attachmentArmKey = ""' in view,
        "Changing the pinned Room disarms attachment")
require('Math.random().toString(36)' in view
        and 'Date.now().toString(36)' in view,
        "New Session ID generated only during user ARM click")
require('root.attachmentArmKey = "";' in view
        and 'attachmentAction.attach(candidate)' in view,
        "Confirmation is single-shot and sends frozen exact candidate")
require('root.runtimeStatusVerified = false;' in view
        and 'root.refreshRequested();' in view,
        "Successful registration invalidates stale runtime status")
require('PROVIDER NOT LAUNCHED' in view
        and 'No AI launch or authority' not in view,
        "Never declare a started worker after Session registration")
require('Not a ChatGPT browser tab' in view
        and 'CHAT is read-only' in view,
        "Browser attachment and Chat limitations remain explicit")
require('No command is sent by opening this panel.' in view,
        "Original Quick no-auto-dispatch rule preserved")
require('ConnectionPolicy.allowsCommand(root.roomData, command)' in view
        and 'SessionPolicy.canIssueQuick(' in view,
        "QUICK still uses prior Session + connection gates")
require('mutationAuthorized: false' in preview,
        "Pure read-only preview never grants permission")
require('roomId: root.active && root.viewMode === "attachPreview"' in view
        and '? root.pinnedRoomId : ""' in view,
        "Assignment reader pinned to exact registered Room")
require('"hospital", "assignments"' in reader
        and '"--room-id", id' in reader,
        "Assignment browsing is read only")

require('function attach(candidate)' in actor
        and 'process.exec([' in actor,
        "PX commit only through isolated click-driven writer")
require('"agent", "session-attach"' in actor
        and '"--mode", pending.mode' in actor
        and '"--confirm", "--json"' in actor,
        "PX atomic command and explicit confirmation are required")
require('"--room-id", pending.roomId' in actor
        and '"--session-id", pending.sessionId' in actor
        and '"--assignment-id", pending.assignmentId' in actor
        and '"--doctor-id", pending.doctorId' in actor
        and '"--provider-id", pending.providerId' in actor
        and '"--working-directory", pending.bedPath' in actor,
        "Never guess or substitute a Room, Session, Doctor, Provider or Bed")
require('if (running || process.running)' in actor
        and 'running = true;' in actor,
        "Repeated click cannot start a second concurrent attachment client")
require('payload.providerLaunched !== false' in actor
        and 'payload.authorityVerified !== false' in actor
        and 'payload.browserChatConnected !== false' in actor,
        "Only accept explicit no-execution/no-authority PX result")
require('root.attached(payload);' in actor
        and 'root.refused(reason);' in actor,
        "Do not report success until PX returns a matching result")
for unsafe in ('"session-put"', '"session-create"', '"room-bind"',
               '"orchestrate-ready"', '"quick"', '"turn"'):
    require(unsafe not in actor, "Writer must not fall back to " + unsafe)
require('HospitalRegisteredWorkerView {' in host
        and 'roomData: root.rosterFocusedRoomData' in host,
        "Preserve exact registered Room caller and existing view")
require('onRefreshRequested: {' in host
        and 'responsibilityService.refreshDurableGraph();' in host,
        "Registry refreshed after successful PX acknowledgement")

if issues:
    print("HOSPITAL ATOMIC ATTACH UI CONTRACT // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL ATOMIC ATTACH UI CONTRACT // PASS // two-click, pinned identity, backend-result verification")
