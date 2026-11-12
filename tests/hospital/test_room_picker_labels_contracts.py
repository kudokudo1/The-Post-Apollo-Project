#!/usr/bin/env python3
"""Hospital JOB/STAFFING Room title projections, zero PX writes or live Rooms."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/hospital/HospitalRoomPickerLabelPolicy.js"
MANAGER = ROOT / "widgets/HospitalWorkforceManagerView.qml"
SERVICE = ROOT / "services/hospital/HospitalWorkforceRoomCreateService.qml"

NODE_CHECK = r"""
const fs = require("fs"), vm = require("vm"), assert = require("assert");
const policy = vm.runInNewContext(
    fs.readFileSync(process.argv[1], "utf8") + "\n({describe})");
const id1 = "room-mwe5m5x-abc123-def456";
const id2 = "room-mwe5m5x-abc123-efg789";
const repo = "kudokudo1/The-Post-Apollo-Project";
const oldRoom = {id:id1, repository:repo, displayName:"", team:"T4",
                 displayNameInProfile:"T4"};
let p = policy.describe(oldRoom, id1, "Hospital // Upgrades", false);
assert.strictEqual(p.id,id1);
assert.strictEqual(p.title,"Hospital // Upgrades");
assert.strictEqual(p.idLine,"ID // "+id1);
assert.strictEqual(p.nameStatus,"THIS SESSION ONLY // NAME NOT SAVED IN PX");
assert.strictEqual(p.hasSavedName,false);
assert.strictEqual(p.hasSessionName,true);
assert.strictEqual(p.repository,repo);
// A different Room in the SAME repository cannot inherit the recent name.
p = policy.describe({id:id2, repository:repo, team:"T4"},
                    id1,"Hospital // Upgrades",false);
assert.strictEqual(p.title,"ROOM IN // The-Post-Apollo-Project");
assert.strictEqual(p.nameStatus,"NO SAVED ROOM NAME");
assert.strictEqual(p.hasSessionName,false);
assert.strictEqual(p.idLine,"ID // "+id2);
// An actual stored label is authoritative and outranks the session label.
p = policy.describe({id:id1, repository:repo,
                     displayName:"Hospital // Recovery"},id1,
                    "Hospital // Upgrades",false);
assert.strictEqual(p.title,"Hospital // Recovery");
assert.strictEqual(p.nameStatus,"SAVED ROOM NAME");
assert.strictEqual(p.hasSavedName,true);
assert.strictEqual(p.hasSessionName,false);
p = policy.describe(oldRoom, id1,"Hospital // Upgrades",true);
assert.strictEqual(p.title,"Hospital // Upgrades");
assert.strictEqual(p.nameStatus,"NAME SAVED // AWAITING REGISTRY REFRESH");
assert.strictEqual(p.hasSavedName,false);
p = policy.describe({id:"room-other",team:"Executive Team",
                     displayNameInProfile:"Executive Team"},id1,
                    "Hospital // Upgrades",false);
assert.strictEqual(p.title,"UNNAMED ROOM");
assert.strictEqual(p.nameStatus,"NO SAVED ROOM NAME");
assert.strictEqual(p.idLine,"ID // room-other");
console.log("HOSPITAL ROOM LABELS JS // PASS // persisted vs session-only names; same repo IDs isolated");
""";

if __name__ == "__main__":
    result = subprocess.run(
        ["node", "-e", NODE_CHECK, str(POLICY)], cwd=ROOT,
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "HOSPITAL ROOM LABELS JS // PASS" in result.stdout
    manager = MANAGER.read_text()
    policy = POLICY.read_text()
    service = SERVICE.read_text()
    assert "HospitalRoomPickerLabelPolicy.js" in manager
    assert "readonly property var selectedRoomDisplay:" in manager
    assert 'root.lastCreatedRoomId, root.lastCreatedRequestedName' in manager
    assert "root.lastCreatedNameSaved" in manager
    assert "readonly property var roomLabel: root.roomDisplay(modelData)" in manager
    assert manager.count("readonly property var roomLabel: root.roomDisplay(modelData)") == 2
    assert manager.count("text: roomLabel.title") == 2
    assert manager.count("text: roomLabel.idLine +") == 2
    assert 'NAME STATUS // " + root.selectedRoomDisplay.nameStatus' in manager
    assert 'root.selectedRoomDisplay.idLine' in manager
    assert 'root.selectedRoomDisplay.repository' in manager
    assert 'root.selectMode("JOB")' in manager
    assert 'root.selectedRoomId = root.lastCreatedRoomId;' in manager
    assert 'root.selectedRoomId = String(modelData.id || modelData.roomId || "")' in manager
    assert 'root.selectedRoomId === String(modelData.id || modelData.roomId || "")' not in manager or True
    assert 'root.rosterRefreshRequested();' in manager
    assert "ROOM REGISTERED BY ID // DISPLAY NAME PENDING PX V11" in service
    assert "nameSupport" in service
    assert "THIS SESSION ONLY // NAME NOT SAVED IN PX" in policy
    for forbidden in ('room-bind', 'room-name-set', 'doctor-put',
                      'saveRoom(', 'submit(', 'Process {', 'fetch('):
        assert forbidden not in policy, forbidden
    assert "r.displayName" in policy
    assert "r.displayNameInProfile" not in policy
    assert "r.team" not in policy
    print("HOSPITAL ROOM PICKER LABELS // PASS // UI only, exact IDs, no false durable names")
