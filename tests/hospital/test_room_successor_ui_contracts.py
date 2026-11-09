#!/usr/bin/env python3
"""Hospital successor preflight contracts. No PX mutation, browser or Session launch."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
host = (root / "widgets/HospitalRegisteredWorkerView.qml").read_text()
room = (root / "widgets/HospitalRoomContinuityView.qml").read_text()
view = (root / "widgets/HospitalRoomSuccessorView.qml").read_text()
policy = (root / "services/hospital/HospitalRoomSuccessorPreviewPolicy.js").read_text()
service = (root / "services/hospital/HospitalRoomContinuityService.qml").read_text()
issues = []


def check(ok, reason):
    if not ok:
        issues.append(reason)


check('HospitalRoomContinuityView {' in host
      and 'roomId: active ? root.pinnedRoomId : ""' in host,
      "Original Room identity must remain pinned")
check('availableDoctors: root.availableDoctors' in host
      and 'availableProviders: root.availableProviders' in host,
      "Must reuse current Hospital registered directories")
check('sessionsLoaded: root.sessionsSnapshotLoaded' in host
      and 'roomsLoaded: root.roomsSnapshotLoaded' in host,
      "Must distinguish verified registries from missing source records")
check('sourceError: root.attachmentSourceError' in host,
      "Source failures cannot be concealed from succession gate")
check('label: "CHAT // SAVED"' in host and 'label: "QUICK // PX"' in host
      and 'label: "CONNECTIONS"' in host,
      "Original Chat, Quick and Links controls must remain")
check('SessionPolicy.canIssueQuick(' in host
      and 'ConnectionPolicy.allowsCommand(' in host,
      "Recovery preview must not bypass actual worker turn guards")

check('label: "RECOVER ROOM"' in room
      and 'onTriggered: root.recoveryOpen = true' in room,
      "Room continuity exposes recovery entry")
check('onRoomIdChanged: recoveryOpen = false' in room,
      "Changing Rooms must close stale recovery panel")
check('HospitalRoomSuccessorView {' in room
      and 'active: root.active && root.recoveryOpen' in room,
      "Successor view loads only on operator request")
check('overview: root.overview' in room
      and 'snapshot: continuity.snapshot' in room,
      "Recovery reuses same pinned durable Room data")
check('onReturnRequested: root.recoveryOpen = false' in room,
      "Return to permanent Room briefing without reassigning staff")
check('registryRefreshRequested()' in room
      and 'onRegistryRefreshRequested: root.refreshRequested()' in host,
      "Operator refresh revalidates current Room and directories")

check('function preview(a)' in policy and 'function briefing(a)' in policy,
      "Pure deterministic successor plan must be separate from display")
check('mutationAuthorized:false' in policy
      and 'operatorApprovalRequired:true' in policy,
      "Preflight must never authorize attachment")
check('str(v.authorRole)' not in policy,
      "Use already vetted operator Chart projection, not a guessed authority")
check('overview.verified === true' in policy
      and 'v(room.id) === roomId' in policy,
      "No reliance on display labels, Git Teams, or foreign Room identity")
check('u(linkedAssignment.status) !== "ACTIVE"' in policy,
      "Preserve linked active work contract")
check('No checkpoint or HANDOFF report' in policy,
      "Missing continuity evidence must be called out")
check('Current Room Session still claims this Room' in policy,
      "Saved Session ownership does not disappear because provider may be offline")
check('active/operating evidence' in policy
      and 'Multiple nonterminal Sessions' in policy,
      "Do not replace over operating/busy or multiply-owned Room")
check('same recorded Bed' in policy
      and 'Selected Doctor has an open Session in another Room' in policy,
      "Protect other Room ownership and successor workload")
check('does not prove an external browser chat died' in policy,
      "No guessed browser death or hidden browser connectivity")
check('Room Doctor identity differs between roster' in policy,
      "Conflicting registered staffing must block")
check('FULL CONTEXT MUST BE REBUILT FROM CURRENT PX RECORDS' in policy,
      "Preview is not the runtime authority context")
check('NO ROOM MUTATION // NO NEW SESSION' in policy,
      "No false registration claim")

check('id: recoveryScroll' in view
      and 'flickable: recoveryScroll' in view,
      "Long recovery review must scroll with native styling")
check('readonly property int pageSize: 8' in view
      and 'root.doctors.slice(' in view
      and 'root.providers.slice(' in view,
      "Render bounded successor and provider choices")
check('root.successorDoctorId = String(modelData.id || "")' in view
      and 'root.successorProviderId = String(modelData.id || "")' in view,
      "Explicit selections only; never guess worker identity")
check('onRoomIdChanged:' in view
      and 'successorDoctorId = ""' in view
      and 'successorProviderId = ""' in view,
      "Room switch must discard old proposed successor")
check('onOverviewChanged: prepared = false' in view
      and 'onSessionsChanged: {' in view
      and 'previousSessionId = ""' in view,
      "A saved preview and selected predecessor must reset on changed Session evidence")
check('label: "PREPARE HANDOFF BRIEF // NO WRITES"' in view,
      "Operator can explicitly inspect briefing without executing it")
check('enabledAction: root.plan.contextAvailable' in view
      and 'onTriggered: root.prepared = true' in view,
      "Do not prepare briefing from unverified Room")
check('onReturnRequested: root.recoveryOpen = false' in room,
      "Back from recovery cannot mutate the Room")
check('No PX transfer, Session mutation' in view
      and 'TRANSFER NOT AUTHORIZED' in view,
      "Claims remain accurate")
check('function successionContract(a)' in policy
      and 'latest insertion order must be verified by PX' in policy
      and 'mutationAuthorized: false' in policy,
      "Read-only exact predecessor contract must fail closed on ambiguous history")
check('readonly property var transfer: SuccessorPolicy.successionContract' in view
      and 'PREDECESSOR SESSION //' in view
      and 'SUCCESSION HOLD //' in view,
      "Recovery UI must show pinned previous Session and failed release prerequisites")
check('NO REPLACEMENT BUTTON YET' in view
      and 'PX authority and atomic revalidation remain mandatory' in view,
      "No direct Doctor transfer without authenticated PX authority")
check('readonly property var predecessorSessions:' in view
      and 'root.predecessorSessions.length > 1' in view
      and 'onClicked: root.previousSessionId' in view
      and 'predecessorPage' in view,
      "Allow explicit history selection only when several prior Sessions exist")
check('previousSessionId: root.previousSessionId' in view
      and 'PX WILL VERIFY LATEST' in view,
      "Pass selected predecessor only to the read-only backend-check contract")
for forbidden in ('Process {', 'session-put', 'room-bind', 'session-create',
                  'assignment-activate', 'doctor-put', 'agent turn',
                  'quick("GO")', 'pxArgs('):
    check(forbidden not in view and forbidden not in policy,
          "No write or execution path in recovery surface: " + forbidden)
check('reader.exec(root.pxArgs(commands[stage]))' in service,
      "Existing read-only sequential Room service remains the sole data source")

if issues:
    print("HOSPITAL SUCCESSOR RECOVERY UI // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL SUCCESSOR RECOVERY UI // PASS // permanent Room, selected successor, truthful continuity and no writes")
