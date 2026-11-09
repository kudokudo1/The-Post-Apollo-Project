#!/usr/bin/env python3
"""Staffing stays inside Surgery and prepares a safe, read-only Room handoff."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
host = (root / "widgets/HospitalW.qml").read_text()
manager = (root / "widgets/HospitalWorkforceManagerView.qml").read_text()
policy = (root / "services/hospital/HospitalWorkforceStaffingPolicy.js").read_text()
assignment_reader = (root / "services/hospital/HospitalWorkerAttachmentPreviewService.qml").read_text()
errors = []

def check(ok, message):
    if not ok:
        errors.append(message)

check('HospitalWorkforceManagerView {' in host
      and 'providerService: providerService' in host
      and 'root.workforceManagerExpanded' in host,
      "Provider directory wired to existing inline Surgery manager")
check('onOpenRoomRequested: function(roomId)' in host
      and 'root.openRosterSession(row, "connections")' in host
      and 'root.workforceRosterRows.filter(' in host,
      "Open Room must reuse existing nested worker inspector")
check('import "../services/hospital/HospitalWorkforceStaffingPolicy.js" as StaffingPolicy'
      in manager
      and 'readonly property var staffingPlan: StaffingPolicy.plan({' in manager,
      "Staffing must have a dedicated pure read-only policy")
check('code:"STAFFING"' in manager
      and 'root.mode === "STAFFING"' in manager
      and 'id: staffingColumn' in manager,
      "Staffing stays in the same expandable WORKERS/ROOM/JOB menu")
check('HospitalWorkerAttachmentPreviewService {' in manager
      and 'id: staffingAssignments' in manager
      and 'roomId: root.active && root.mode === "STAFFING"' in manager
      and '"hospital", "assignments"' in assignment_reader,
      "Read exact saved Assignments using existing Room-scoped PX reader")
check('selectedStaffDoctorId' in manager
      and 'selectedStaffProviderId' in manager
      and 'root.doctors.slice(' in manager
      and 'root.providers.slice(' in manager,
      "Select Doctor and Provider from saved directories rather than text IDs")
check('root.staffingPlan.blockers.slice(' in manager
      and 'root.staffingPlan.notes' in manager
      and 'root.staffingPlan.bedPath' in manager
      and 'root.staffingPlan.branch' in manager,
      "Show Bed, branch and precise missing prerequisites to operator")
check('function reviewStaffing()' in manager
      and 'root.staffingReviewKey = root.staffingSignature;' in manager
      and 'function openStaffingRoom()' in manager
      and 'root.openRoomRequested(id);' in manager,
      "Review pins registry snapshot for inspection then only navigates")
check('onStaffingPlanChanged: staffingReviewKey = ""' in manager
      and 'onSelectedStaffDoctorIdChanged: staffingReviewKey = ""' in manager
      and 'onSelectedStaffProviderIdChanged: staffingReviewKey = ""' in manager,
      "Changing source identities invalidates reviewed plan")
check('authorizationVerified: false' in policy
      and 'mutationAuthorized: false' in policy
      and 'providerLaunched: false' in policy
      and 'sessionCreated: false' in policy,
      "Staffing preview never confers authority or Session execution")
check('Room belongs to another Doctor' in policy
      and 'Git Bed already assigned to another Room' in policy
      and 'Doctor has an unreleased Session elsewhere' in policy,
      "Refuse existing ownership and Session collisions")
check('First-worker pilot requires an ACTIVE READ-only Assignment' in policy
      and 'Room Git branch or working Bed missing' in policy
      and 'Staffing PREPARED' not in policy,
      "Fail closed on missing or elevated work context without a writer")
for forbidden in ('Process {', 'room-bind', 'doctor-put', 'session-attach',
                  'session-succeed', 'assignment-activate', 'agent turn'):
    check(forbidden not in policy, "Pure staffing policy cannot issue commands: " + forbidden)
check('"NO STAFFING WRITER // Backend authority and atomic ownership check still required"'
      in manager,
      "Show honest next authority dependency in review UI")
if errors:
    print("HOSPITAL SURGERY STAFFING REVIEW // FAIL")
    for failure in errors:
        print(" - " + failure)
    raise SystemExit(1)
print("HOSPITAL SURGERY STAFFING REVIEW // PASS // no mutation, exact Room/Doctor/Provider inspection")
