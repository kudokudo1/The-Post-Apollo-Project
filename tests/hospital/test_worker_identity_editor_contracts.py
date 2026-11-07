#!/usr/bin/env python3
"""Hospital editable worker identity: no technical identity rewrites."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
host = (root / "widgets/HospitalW.qml").read_text(encoding="utf-8")
service = (root / "services/hospital/HospitalRoomNameService.qml").read_text(encoding="utf-8")
projection = (root / "services/hospital/HospitalWorkforceRosterPolicy.js").read_text(encoding="utf-8")
responsibility = (root / "services/hospital/HospitalResponsibilityService.qml").read_text(encoding="utf-8")
failures = []


def check(value, message):
    if not value:
        failures.append(message)


check("HospitalRoomNameService {" in host, "new isolated Room name service")
check("roomNameService.saveName(" in host, "Room names saved through explicit PX operation")
check('"room-name-set"' in service, "only PX room-name-set permitted")
check('"room-put"' not in service, "must not rewrite full Room identity")
check('"room-bind"' not in service, "must not bind or create Room in label editor")
check('"agent"' not in service, "name edit must not launch worker turns")
check("root.rosterEditingRoomId" in host, "Room is identified by durable ID")
check("room.nameIsFallback" in host, "empty editor means reset alias, not rename ID")
check('text: "ASSIGNMENT // "' in host, "visible Assignment identity")
check("rosterRow.rosterData.assignmentTitle" in host, "linked Assignment title displayed")
check("assignmentTitle: textValue(room.assignmentTitle)" in projection,
      "only real linked Assignment data")
check("doctorService.doctorById(id)" in host,
      "Doctor must already be registered for rename")
check("doctor.id, name, doctor.role, doctor.status" in host,
      "Doctor rename preserves role/status")
check('root.rosterEditingRoomId = ""' in host, "editor cancellation resets target")
check("root.rosterIdentityRefreshPending" in host,
      "queued refresh prevents stale roster after successful edit")
check("REGISTERED PX ROOM" not in host or "SHOW BRANCHES" in host,
      "original branch view remains available")
check("model: root.workforceRosterVisible ? [] : auditService.rooms" in host,
      "editing does not replace Git branch list")
check('repository !== selected' in host, "cross-Patient Git navigation remains gated")
check("lastSavedRoom" in service and "result.id" in service,
      "PX reply checked for target Room ID")
check("onNameSaved:" in host, "successful label write causes roster reload")
check("PX V11" in service, "older PX runtime produces actionable error")
check("post-apollo-dev-runtime/bin/px" in responsibility
      and "post-apollo-dev-runtime/bin/px" in service,
      "registry and writes select same PX version")
check("function saveRosterDoctorName()" in host,
      "Doctor rename action explicitly named")

if failures:
    print("HOSPITAL WORKER NAME EDITOR // FAIL")
    for failure in failures:
        print(" - " + failure)
    raise SystemExit(1)

print("HOSPITAL WORKER NAME EDITOR // PASS // separate names, stable identities, preserved branch view")
