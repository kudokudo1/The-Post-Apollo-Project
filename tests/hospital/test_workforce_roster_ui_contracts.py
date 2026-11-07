#!/usr/bin/env python3
"""Contract for the read-only Hospital workforce roster pilot."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
host = (root / "widgets/HospitalW.qml").read_text(encoding="utf-8")
policy = (root / "services/hospital/HospitalWorkforceRosterPolicy.js").read_text(
    encoding="utf-8"
)
issues = []


def required(test, message):
    if not test:
        issues.append(message)


required(
    'import "../services/hospital/HospitalWorkforceRosterPolicy.js" as WorkforceRosterPolicy' in host,
    "Surgery must import the isolated workforce projection",
)
required(
    "readonly property var workforceRosterRows: WorkforceRosterPolicy.buildRoster(" in host,
    "Roster must use registered PX Rooms/Sessions and Doctor directory",
)
required(
    "responsibilityService.durableRooms" in host
    and "responsibilityService.durableSessions" in host,
    "Roster source must be durable Hospital records, not audit branches",
)
required(
    "doctorService.doctors" in host,
    "Doctor display names must remain distinct from Room identifiers",
)
required(
    "REGISTERED WORKERS" in host
    and "SHOW BRANCHES" in host
    and "SHOW WORKERS" in host,
    "The operator must be able to distinguish and switch views",
)
required(
    "model: root.workforceRosterVisible ? [] : auditService.rooms" in host,
    "Legacy Git room list must remain available",
)
required(
    "model: root.workforceRosterVisible" in host
    and "? root.workforceRosterRows : []" in host,
    "Worker rows must not be aliases of the branch audit",
)
required(
    "rosterCurrentRoomIndex" in host
    and "repository !== selected" in host,
    "Cross-Patient row must not select a same-named Git Room",
)
required(
    "if (!repository || !selected || repository !== selected || !team)" in host,
    "Missing Patient/Room identity must fail closed for navigation",
)
required(
    "REGISTERED PX ROOM // OTHER FLOOR OR NO GIT MATCH" in host,
    "Unlinked workers must be shown honestly",
)
required(
    "function buildRoster(rooms, sessions, doctors)" in policy
    and "if (!id || seen[id])" in policy,
    "The registry must use unique persistent Room IDs",
)
required(
    'sessionStatus: rawStatus' in policy
    and '"NO SESSION"' in policy
    and "hasActiveSession: !!activeSession" in policy,
    "Absent sessions must not masquerade as running workers",
)
required(
    "function setWorkforceRosterVisible(nextValue)" in host
    and "responsibilityService.refreshDurableGraph();" in host,
    "Registered workforce data must refresh when inspected",
)
required(
    "readonly property var mainModeOrder:" in host,
    "Main Hospital tab structure must not be removed",
)

if issues:
    print("HOSPITAL WORKFORCE ROSTER UI // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL WORKFORCE ROSTER UI // PASS // read-only pilot and legacy branch view")
