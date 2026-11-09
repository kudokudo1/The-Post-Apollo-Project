#!/usr/bin/env python3
"""Surgery's saved-job activation is in-place, reviewed and launches no AI."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
view = (root / "widgets/HospitalWorkforceManagerView.qml").read_text()
policy = (root / "services/hospital/HospitalWorkforceJobActivationPolicy.js").read_text()
issues = []
def check(ok, msg):
    if not ok:
        issues.append(msg)

check('import "../services/hospital/HospitalWorkforceJobActivationPolicy.js" as JobActivationPolicy' in view,
      "Add isolated policy in the current Surgery manager only")
check('readonly property var activationPlan: JobActivationPolicy.review({' in view
      and 'rooms: root.rooms' in view and 'sessions: root.sessions' in view
      and 'assignments: inlineAssignment.assignments' in view,
      "Require durable Room / Session and saved Job evidence")
check('function reviewActivation()' in view
      and 'function confirmActivation()' in view
      and 'activationArmKey !== activationSignature' in view
      and 'activationArmKey = "";' in view,
      "Separate explicit review and one-shot confirm")
check('inlineAssignment.activateAssignment(id)' in view
      and 'onAssignmentActivated: function(result)' in view,
      "Use existing backend activation and verify exact returned identities")
check('String(assignment.status || "") !== "ACTIVE"' in view
      and 'String(room.assignmentId || "")' in view,
      "Match actual ACTIVE Assignment and linked Room response")
check('root.assignmentListVerified = false' in view
      and 'onAssignmentsRefreshed:' in view
      and 'onSelectedRoomIdChanged:' in view,
      "Clear stale selections and require refreshed Assignment read")
check('selectedDraftAssignmentId: ""' in view
      and 'root.selectedDraftAssignmentId' in view
      and 'SAVED JOBS // CHOOSE READ-ONLY DRAFT TO ACTIVATE' in view,
      "Select a specific saved draft from the same JOB section")
check('ACTIVATE marks a job ACTIVE and links it to this Room' in view
      and 'It does NOT start an AI' in view
      and 'NO AI LAUNCHED' in view,
      "Explain actual persistence effect without promising worker execution")
check('root.activationPlan.blockers.join(" // ")' in view
      and 'CONFIRM ACTIVE' in view
      and 'REVIEW ACTIVE' in view,
      "Show blockers and explicit activation buttons")
for name in ("terminalReleased", "function review(source)", "assignmentsLoaded",
             "Another ACTIVE Assignment", "Only a saved DRAFT", "requires READ-only",
             "Session not explicitly released", "Room already has an active Assignment"):
    check(name in policy, "Fail-closed backend contract: " + name)
for name in ('"agent", "turn"', '"agent", "quick"', 'session-create',
             'orchestrate-ready', 'session-succeed'):
    check(name not in policy, "No runtime action in activation policy: " + name)
if issues:
    print("SURGERY FIRST JOB ACTIVATION // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("SURGERY FIRST JOB ACTIVATION // PASS // exact reviewed draft only, no AI launch")
