#!/usr/bin/env python3
"""Hospital worker connection inspection; no new provider attachments."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
roster = (root / "services/hospital/HospitalWorkforceRosterPolicy.js").read_text()
policy = (root / "services/hospital/HospitalWorkerConnectionPolicy.js").read_text()
host = (root / "widgets/HospitalW.qml").read_text()
view = (root / "widgets/HospitalRegisteredWorkerView.qml").read_text()
session = (root / "services/hospital/HospitalWorkerSessionPolicy.js").read_text()
issues = []


def check(ok, message):
    if not ok:
        issues.append(message)


for key in ("roomDoctorId", "sessionDoctorId", "roomProviderId",
            "sessionProviderId", "bedPath", "sessionWorkingDirectory",
            "assignmentId", "assignmentStatus", "sessionId", "sessionStatus",
            "providerSessionId", "sessionActivePid"):
    check(key in roster, "Missing independent roster evidence: " + key)

check("function inspect(roomValue)" in policy and "function allowsCommand(" in policy,
      "Pure policy must classify links and guard worker turns")
check('source: "PX ROOM / SESSION RECORDS"' in policy,
      "Connection source must be explicit")
check("isProviderReachable: false" in policy
      and "isBrowserChatConnected: false" in policy,
      "Saved PX records must not claim provider/browser connectivity")
check("status === \"REVIEW\" || status === \"WAITING\"" in policy
      and 'code = "SESSION_PAUSED"' in policy,
      "Paused or held workers must not accept blind continuation")
check('provider === "int1-fake"' in policy,
      "Fake-only provider must not enter standard Quick path")
check("roomBed !== sessionBed" in policy,
      "Different Bed identities must be blocked pending PX verification")
check('command === "STATUS"' in policy and 'command === "PAUSE"' in policy,
      "Inspection and emergency pause are separate from new worker turns")

check('import "../services/hospital/HospitalWorkerConnectionPolicy.js" as WorkerConnectionPolicy' in host,
      "Surgery imports exact registered worker connection policy")
check("WorkerConnectionPolicy.countPending(root.workforceRosterRows)" in host,
      "Visible roster counts unresolved worker links")
check("WorkerConnectionPolicy.inspect(rosterData)" in host,
      "Every worker card gets its own saved binding diagnosis")
check('"LINK // " + rosterRow.connection.label' in host,
      "Worker card displays an actionable connection indicator")
check("rosterRow.connection.next" in host,
      "Operator can see what step is needed")
check('label: "LINKS"' in host and '"connections")' in host,
      "Each worker has direct registered-Room connection details")
check('root.rosterFocusedMode = modeValue === "connections" ? "connections"' in host,
      "Selected Room is pinned before opening connections panel")
check('root.rosterFocusedSessionId = String(current.sessionId || "")' in host,
      "Connections must not change Session selection")
check('root.workforceRosterVisible ? [] : auditService.rooms' in host,
      "Legacy Git Room list stays untouched")

check("ConnectionPolicy.inspect(root.roomData)" in view,
      "Details derive from same exact durable Room")
check('root.viewMode === "connections"' in view
      and 'id: connectionsScroll' in view,
      "Connection checklist has its own scrollable screen")
check('model: root.connectionPlan.checks' in view,
      "Checklist must cover Room, Doctor, Provider, Assignment, Bed, Session")
check("root.connectionPlan.next" in view
      and "root.connectionPlan.label" in view,
      "Actionable blockers visible in the inspector")
check("ConnectionPolicy.allowsCommand(root.roomData, command)" in view,
      "Quick function enforces structural connection guard")
check("ConnectionPolicy.allowsCommand(" in view
      and "enabledAction: root.canCommand" in view,
      "Quick UI disables unsupported worker turns")
check("SessionPolicy.canIssueQuick(" in view,
      "Prior exact-ID Session guard remains authoritative")
check("SessionPolicy.sessionMatches(" in view
      and "SessionPolicy.statusMatches(" in view,
      "Exact Room and Session identity still required")
check("runtime.quick(command)" in view,
      "Existing explicit backend Quick command path retained")
check("runtime.refresh()" in view,
      "Fresh PX status read remains required for Quick")
check("A status read proves the PX record was accessible" in view
      and "Not a ChatGPT browser tab" in view,
      "No false live provider or browser connection claims")
check("CHAT is read-only" in view, "Previous Chat limitation remains explained")
check('text: "PX STATUS READ // "' in view,
      "PX database status must not masquerade as a live heartbeat")
check("sessionMatches(roomData, roomId, sessionId)" in session,
      "No structural link can bypass Session identity policy")

for forbidden in ("session-put", "room-bind", "doctor-put",
                  "assignment-activate", "provider-connect",
                  "browser-attach", "orchestrate-ready"):
    check(forbidden not in policy, "Read-only connection policy must not mutate: " + forbidden)

if issues:
    print("HOSPITAL WORKER CONNECTION UI // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL WORKER CONNECTION UI // PASS // exact identities, honest readiness, no attachments")
