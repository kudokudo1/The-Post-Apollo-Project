#!/usr/bin/env python3
"""Hospital attachment preview source contracts. No PX or live desktop writes."""
from pathlib import Path

base = Path(__file__).resolve().parents[2]
host = (base / "widgets/HospitalW.qml").read_text()
view = (base / "widgets/HospitalRegisteredWorkerView.qml").read_text()
reader = (base / "services/hospital/HospitalWorkerAttachmentPreviewService.qml").read_text()
policy = (base / "services/hospital/HospitalWorkerAttachmentPreviewPolicy.js").read_text()
issues = []


def check(condition, reason):
    if not condition:
        issues.append(reason)


check('HospitalWorkerAttachmentPreviewService {' in view,
      "Use an isolated read-only exact-Room Assignment reader")
check('roomId: root.active && root.viewMode === "attachPreview"' in view
      and '? root.pinnedRoomId : ""' in view,
      "Reader cannot follow a guessed Git Team or wrong Room")
check('"hospital", "assignments"' in reader
      and '"--room-id", id' in reader
      and '"--status", "ALL"' in reader,
      "Read only existing Assignments scoped by durable Room ID")
check('String((row || {}).roomId || "") === requested' in reader,
      "Reader must discard foreign Room Assignments")
check('requested === String(root.roomId || "").trim()' in reader,
      "Reader must not display asynchronous results for the previous Room")
check('lastError = "PX ASSIGNMENTS //' in reader,
      "PX read/parse errors must remain visible")
for command in ('"room-bind"', '"session-put"', '"assignment-activate"',
                '"doctor-put"', '"session-create"', '"agent"'):
    check(command not in reader, "Reader must not write: " + command)

check('function openAttachmentPreview()' in view
      and 'root.viewMode === "attachPreview"' in view,
      "Existing CONNECTIONS screen opens a dedicated preview")
check('label: "PREVIEW ATTACHMENT"' in view,
      "Operator has visible entry action")
check('label: "BACK TO CONNECTIONS"' in view,
      "Operator can return without mutating anything")
check('assignmentPreview.assignments' in view
      and 'root.previewAssignmentId' in view,
      "User can select an existing Assignment")
check('root.availableDoctors' in view and 'root.previewDoctorId' in view,
      "User can select a registered Doctor")
check('root.availableProviders' in view and 'root.previewProviderId' in view,
      "User can select an existing Provider")
check('root.attachmentPreview.blockers' in view
      and 'root.attachmentPreview.notes' in view,
      "Blockers and review notes are visible")
check('root.attachmentPreview.facts' in view
      and 'root.attachmentPreview.headline' in view,
      "Exact selection and overall status remain visible")
check('id: attachScroll' in view
      and 'flickable: attachScroll' in view,
      "Preview must scroll with existing Post-Apollo indicator")
check('No attach command is exposed' in view
      and 'NO ATTACHMENT MADE' in view,
      "Preview may never claim it connected a worker")
check('ConnectionPolicy.allowsCommand(root.roomData, command)' in view
      and 'SessionPolicy.canIssueQuick(' in view,
      "Existing Quick identity and authority gates retained")

check('availableDoctors: doctorService.doctors' in host
      and 'availableProviders: providerService.providers' in host,
      "Use existing Hospital Doctor and Provider services")
check('allRooms: responsibilityService.durableRooms' in host
      and 'allSessions: responsibilityService.durableSessions' in host,
      "Reuse existing durable Room/Session registry")
check('roomsSnapshotLoaded: responsibilityService.roomsLoaded' in host
      and 'sessionsSnapshotLoaded: responsibilityService.sessionsLoaded' in host,
      "Missing snapshots must be explicitly distinguished")
check('providerService.refresh();' in host
      and 'doctorService.refresh();' in host,
      "Preview open must refresh source directories")
check('onCloseRequested: root.showSurgery()' in host,
      "Original Surgery navigation remains")
check('root.rosterFocusedRoomId' in host
      and 'root.rosterFocusedSessionId' in host,
      "Exact Room and Session pins retained")

check('mutationAuthorized: false' in policy,
      "Preview must not grant authority or change registration")
check('Another Room has an open Session on the same recorded Bed' in policy,
      "Cross-Room Bed collision must block")
check('Multiple nonterminal Sessions' in policy,
      "Existing active Session collisions must block")
check('Assignment belongs to another Room' in policy,
      "Assignment ownership may not cross a Room boundary")
check('status(doctor.status) !== "ACTIVE"' in policy,
      "Inactive Doctor must not be proposed")
check('provider.available !== true' in policy,
      "Unavailable provider must not be proposed")
check('Fake-only provider requires separate synthetic authorization' in policy,
      "Fake-only provider requires separate authorization")
check('Session Provider differs from selected Provider' in policy,
      "Session provider mismatch must block")
check('Existing Session is not IDLE' in policy,
      "No new turn is allowed over busy or held Session")
check('!a.assignmentsLoaded' in policy and '!a.sessionsLoaded' in policy,
      "Missing snapshots must fail closed")
check('source: "READ-ONLY PX REGISTRY PREVIEW"' in policy,
      "Provenance remains explicit")
for forbidden in ('session-put', 'room-bind', 'assignment-activate',
                  'provider-launch', 'quick("GO")'):
    check(forbidden not in policy, "Pure preview must not invoke: " + forbidden)

if issues:
    print("HOSPITAL ATTACHMENT PREVIEW UI // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL ATTACHMENT PREVIEW UI // PASS // read-only guided selection, identity and collision gates")
