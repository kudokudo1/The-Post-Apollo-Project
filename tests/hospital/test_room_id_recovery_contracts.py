#!/usr/bin/env python3
"""Hospital Room creation: v10 naming compatibility, ID safety, visible recovery.

Source contracts only. No connection to installed PX, database, or Room writes.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "services/hospital/HospitalWorkforceRoomCreateService.qml").read_text()
MANAGER = (ROOT / "widgets/HospitalWorkforceManagerView.qml").read_text()
POLICY = (ROOT / "services/hospital/HospitalWorkforceManagerPolicy.js").read_text()
HOST = (ROOT / "widgets/HospitalW.qml").read_text()
issues = []


def check(condition, description):
    if not condition:
        issues.append(description)


check('property string nameSupport: "CHECKING"' in SERVICE
      and 'function probeNameSupport()' in SERVICE
      and 'Component.onCompleted: probeNameSupport()' in SERVICE
      and '"hospital", "room-name-set", "--help"' in SERVICE
      and 'nameSupport = Number(code) === 0' in SERVICE,
      "PX naming capability checked via read-only CLI help before create")
check('if (nameSupport === "CHECKING")' in SERVICE
      and 'PX CAPABILITY CHECK RUNNING // ROOM NOT WRITTEN' in SERVICE,
      "No writes while backend capability is unknown")
check('id: lookupProcess' in SERVICE
      and 'lookupProcess.exec(pxArgs(["hospital", "room", id, "--json"]))' in SERVICE
      and 'unknown Hospital room: ' in SERVICE
      and 'const exists = Number(code) === 0;' in SERVICE
      and 'root.idCollision(id);' in SERVICE
      and 'ROOM REGISTRY UNAVAILABLE // NO WRITE PERFORMED' in SERVICE,
      "Generated ID read-only existence lookup; unknown backend errors fail closed")
check(SERVICE.index('lookupProcess.exec(pxArgs(["hospital", "room", id, "--json"]))')
      < SERVICE.index('bindProcess.exec(root.pxArgs(['),
      "Room-bind may be reached only after read-only ID lookup")
check('if (exists || !absent)' in SERVICE
      and 'root.creating = false;' in SERVICE
      and 'root.pending = ({});' in SERVICE
      and 'if (exists)' in SERVICE
      and 'root.idCollision(id);' in SERVICE,
      "Existing ID must abort instead of overwriting via PX room-bind UPSERT")
check('if (root.nameSupport !== "SUPPORTED")' in SERVICE
      and 'ROOM REGISTERED BY ID // DISPLAY NAME PENDING PX V11' in SERVICE
      and 'root.created(root.savedRoom);' in SERVICE
      and 'root.pending = ({});' in SERVICE,
      "Older PX completes ID-only creation after authoritative bind")
check('nameProcess.exec(root.pxArgs([' in SERVICE
      and '"hospital", "room-name-set", root.pending.id' in SERVICE
      and 'ROOM REGISTERED + NAMED' in SERVICE,
      "PX v11 still writes independent display names")
check('PX NAME SAVE UNSUPPORTED OR FAILED // ROOM ID IS REGISTERED' in SERVICE
      and 'ROOM REGISTERED BY ID // DISPLAY NAME NOT SAVED' in SERVICE
      and 'ROOM " + id + " EXISTS // ' not in SERVICE,
      "Partial success never misreported as Room ID collision or duplicate")
check('property string lastCreatedRoomId: ""' in MANAGER
      and 'property string lastCreatedRequestedName: ""' in MANAGER
      and 'property bool lastCreatedNameSaved: false' in MANAGER
      and 'root.lastCreatedRoomId = savedId;' in MANAGER
      and 'root.selectedRoomId = savedId;' in MANAGER
      and 'root.roomId = root.makeId("room");' in MANAGER
      and 'root.rosterRefreshRequested();' in MANAGER,
      "After confirmed bind, preserve registered Room ID and mint next ID")
check('onIdCollision: function(existingId)' in MANAGER
      and 'root.roomId = root.makeId("room");' in MANAGER
      and 'OLD ROOM UNCHANGED' in MANAGER
      and 'REVIEW AGAIN' in MANAGER,
      "Known collision regenerates ID and disarms review")
check('if (kind === "CREATE_ROOM" && root.rooms.some(function(r)' in MANAGER
      and 'ROOM ID WAS ALREADY REGISTERED // NEW ID GENERATED' in MANAGER
      and 'NO WRITE' in MANAGER
      and 'onRoomsChanged:' in MANAGER
      and 'EXISTING ROOM PRESERVED // FRESH ID GENERATED' in MANAGER,
      "Newly loaded/existing Room ID automatically re-keyed before any action")
check('PX NAME SUPPORT MISSING // CONFIRM CREATES AN ID-ONLY ROOM' in MANAGER
      and 'THE TYPED NAME WILL NOT BE SAVED' in MANAGER
      and 'NEXT ROOM ID // ' in MANAGER
      and 'Automatically generated technical key. It is NOT your Room name.' in MANAGER,
      "Operator sees fallback and technical-ID distinction before confirm")
check('LAST REGISTERED ROOM // ' in MANAGER
      and 'REQUESTED NAME // ' in MANAGER
      and 'DISPLAY NAME NOT SAVED // ROOM EXISTS UNDER ITS ID' in MANAGER
      and 'label: "USE LAST REGISTERED ROOM // NEW JOB"' in MANAGER
      and 'root.selectMode("JOB")' in MANAGER,
      "After creation, preserve and navigate the actual Room instead of reusing error ID")
check('roomCreate.probeNameSupport();' in MANAGER
      and 'ROOM CREATE HOLD // CHECKING INSTALLED PX NAME SUPPORT' in MANAGER,
      "New Room form refreshes name support without mutation")
check('Room ID already exists. Nothing may be overwritten' in POLICY
      and 'onRosterRefreshRequested:' in HOST
      and 'responsibilityService.refreshDurableGraph()' in HOST,
      "Existing list collision preflight and main roster refresh are preserved")
# Room names and Teams are different: no reuse of --team to fake name
check('"--team"' not in SERVICE
      and '"--doctor-id"' not in SERVICE
      and '"--provider-id"' not in SERVICE
      and '"--assignment-id"' not in SERVICE
      and '"--branch"' not in SERVICE,
      "No staffing/Team/branch mutation to emulate unsupported display names")
if issues:
    print("HOSPITAL ROOM ID RECOVERY // FAIL")
    for item in issues:
        print(" - " + item)
    raise SystemExit(1)
print("HOSPITAL ROOM ID RECOVERY // PASS // preflight, v10 ID-only, v11 naming, collision and discoverability")
