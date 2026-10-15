#!/usr/bin/env python3
"""Source-only contract for the real Git REPO INDEX pilot.

Does not assert runtime pointer behavior or service refresh timing.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
slider = (ROOT / "components/SelectorSlider.qml").read_text(encoding="utf-8")
hospital = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
service = (ROOT / "services/git/GitService.qml").read_text(encoding="utf-8")

# Every REPO test starts off. Normal release-to-commit is explicitly opt-in.
assert 'property bool repoIndexPilotEnabled: false' in git
assert 'property bool remoteIndexPilotEnabled: false' in git
assert git.count('indexInteraction: root.repoIndexPilotEnabled') == 1
assert 'indexInteraction: root.remoteIndexPilotEnabled' in git
assert 'LIVE REPO // OFF' in git
assert 'LIVE REPO // ON' in git
assert 'LIVE REMOTE // OFF' in git
assert 'INDEX LAB // TEST' in git

# No global changes: default SelectorSlider and Hospital FLOOR are legacy.
assert 'property string indexInteraction: "legacy"' in slider
assert 'stabilizeLegacyRelease' not in slider
floor = hospital.split("id: floorSlider", 1)[1].split("onIndexRequested:", 1)[0]
assert 'indexInteraction' not in floor

repo = git.split("id: repoSlider", 1)[1].split("id: remoteSlider", 1)[0]
remote = git.split("id: remoteSlider", 1)[1].split(
    "id: sliderIndexLabToggle", 1
)[0]
assert 'indexInteraction: root.repoIndexPilotEnabled' in repo
assert 'gitService.selectRepo(index);' in repo
assert 'indexInteraction: root.remoteIndexPilotEnabled' in remote
assert 'gitService.selectRemote(index);' in remote

# Toggle resets on leaving Git CONTROL, switching pages, or menu close.
assert git.count('repoIndexPilotEnabled = false;') >= 3
assert 'root.repoIndexPilotEnabled = false;' in git

# A selection has meaningful real effects, so do not hide those obligations.
assert 'function selectRepo(index)' in service
assert 'applyRepoRow(row);' in service
assert 'refresh();' in service
assert 'refreshPending = true;' in service

# The accepted ON-mode flick fix is still present.
assert 'property bool previewGestureActive: false' in slider
release = slider.split('onReleased: {', 1)[1].split('onCanceled: {', 1)[0]
assert release.index('slider.indexRequested(finalIndex);') < release.index(
    'slider.previewGestureActive = false;'
)

print("SELECTOR INDEX // GIT REPO OPT-IN PILOT STATIC CONTRACT PASS")
