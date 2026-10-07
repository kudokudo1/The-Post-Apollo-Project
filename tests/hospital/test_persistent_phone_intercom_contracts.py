#!/usr/bin/env python3
"""Contracts for persistent Hospital Phone/Intercom routing."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISPATCH = (
    ROOT / "services/hospital/HospitalPersistentDispatchService.qml"
).read_text(encoding="utf-8")
PHONE = (
    ROOT / "services/hospital/HospitalPhoneService.qml"
).read_text(encoding="utf-8")
INTERCOM = (
    ROOT / "services/hospital/HospitalIntercomService.qml"
).read_text(encoding="utf-8")
RESP = (
    ROOT / "services/hospital/HospitalResponsibilityService.qml"
).read_text(encoding="utf-8")
PHONE_VIEW = (
    ROOT / "widgets/HospitalPhoneMenu.qml"
).read_text(encoding="utf-8")
INTERCOM_VIEW = (
    ROOT / "widgets/HospitalIntercomMenu.qml"
).read_text(encoding="utf-8")
HOSPITAL = (
    ROOT / "widgets/HospitalW.qml"
).read_text(encoding="utf-8")
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


for needle, label in (
    ("function roomForSpecialist(recordValue)", "specialist -> Room mapping"),
    ("matches.length === 1 ? matches[0] : null", "ambiguous owner refusal"),
):
    require(RESP, needle, label)

for needle, label in (
    ("stdinEnabled: true", "JSON-framed safe stdin"),
    ('"--prompt-json-stdin"', "PX safe prompt transport"),
    ('"sessions",', "Room session lookup"),
    ("function compatibleSession", "persistent Doctor resolution"),
    ("MULTIPLE ACTIVE DOCTOR SESSIONS", "ambiguous session refusal"),
    ("NO ACTIVE DOCTOR SESSION", "no-session refusal"),
    ("dispatchCompleted", "persistent delivery completion"),
):
    require(DISPATCH, needle, label)

for needle, label in (
    ("persistentCallRequested", "Phone attach signal"),
    ("roomForSpecialist", "Phone ownership mapping"),
    ("if (!!forceFresh)", "explicit fresh Phone path"),
    ('"RIGHT CLICK FOR FRESH TERMINAL"', "fresh Phone affordance"),
):
    require(PHONE, needle, label)

for needle, label in (
    ("dispatchService.dispatchToRoom", "persistent Intercom dispatch"),
    ("roomForSpecialist", "Intercom ownership mapping"),
    ("if (!!forceFresh)", "explicit detached Intercom path"),
    ('"RIGHT CLICK SEND FOR FRESH TERMINAL"', "fresh Intercom affordance"),
):
    require(INTERCOM, needle, label)

require(
    PHONE_VIEW,
    "Qt.LeftButton | Qt.RightButton",
    "Phone explicit fresh gesture",
)
require(
    PHONE_VIEW,
    "LEFT ATTACH ROOM DOCTOR // RIGHT FRESH TERMINAL",
    "Phone semantics help",
)
require(
    INTERCOM_VIEW,
    "Qt.LeftButton | Qt.RightButton",
    "Intercom explicit fresh gesture",
)

for needle, label in (
    ("HospitalPersistentDispatchService {", "dispatcher host"),
    ("responsibilityService: responsibilityService", "responsibility injection"),
    ("dispatchService: persistentDispatchService", "Intercom dispatcher injection"),
    ("onPersistentCallRequested(roomTeam, specialist)", "Phone Room navigation"),
    ("Qt.callLater(root.openRoomChat)", "Phone attaches visible Room chat"),
):
    require(HOSPITAL, needle, label)

if errors:
    print("POST-APOLLO PERSISTENT PHONE INTERCOM // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO PERSISTENT PHONE INTERCOM // PASS")
print("checked persistent Room routing and explicit fresh-terminal escape hatches")
