#!/usr/bin/env python3
"""Source contract for Hospital's optional real FLOOR INDEX pilot.

This does not certify live Qt behavior or Hospital's state transitions.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
hospital = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
slider = (ROOT / "components/SelectorSlider.qml").read_text(encoding="utf-8")
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
floor = (ROOT / "services/hospital/HospitalFloorService.qml").read_text(encoding="utf-8")

assert 'property bool floorIndexPilotEnabled: false' in hospital
assert hospital.count('indexInteraction: root.floorIndexPilotEnabled') == 1
assert 'LIVE FLOOR // ON' in hospital
assert 'LIVE FLOOR // OFF' in hospital
assert 'enabledSlider: root.floorSwitchEnabled' in hospital

block = hospital.split('id: floorSlider', 1)[1].split('id: fixedTop', 1)[0]
assert 'indexInteraction: root.floorIndexPilotEnabled' in block
assert 'root.selectFloor(index);' in block

# Preserve Hospital authority and existing operating-room safety gates.
assert 'function selectFloor(index)' in hospital
assert 'if (!floorSwitchEnabled)' in hospital
for guard in ('!root.operationsOpen', '!floorService.discovering',
              '!patientService.refreshing', '!roomService.running',
              '!roomService.armed'):
    assert guard in hospital
assert 'floorService.selectFloor(requested);' in hospital
assert 'function selectFloor(index)' in floor

# Leaving Surgery or closing the panel must switch back to legacy.
assert 'if (root.operationsOpen)\n            root.floorIndexPilotEnabled = false;' in hospital
assert 'root.floorIndexPilotEnabled = false;' in hospital
assert 'enabled: root.floorSwitchEnabled\n' in hospital
assert '|| root.floorIndexPilotEnabled' in hospital

# Default shared component and accepted Git behavior are unchanged.
assert 'property string indexInteraction: "legacy"' in slider
assert 'property bool previewGestureActive: false' in slider
assert 'stabilizeLegacyRelease' not in slider
# Only Hospital retains a live test toggle; Git reverts to its intended
# immediate navigation behavior after the completed acceptance exercises.
assert 'LIVE REPO //' not in git
assert 'LIVE REMOTE //' not in git
repo = git.split("id: repoSlider", 1)[1].split("id: remoteSlider", 1)[0]
remote = git.split("id: remoteSlider", 1)[1].split("onIndexRequested:", 1)[1]
assert 'indexInteraction:' not in repo
assert 'indexInteraction:' not in remote
assert 'gitService.selectRepo(index);' in repo
assert 'gitService.selectRemote(index);' in remote

print("SELECTOR INDEX // HOSPITAL FLOOR OPT-IN STATIC CONTRACT PASS")
