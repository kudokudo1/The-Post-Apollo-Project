#!/usr/bin/env python3
"""Post-pilot regression: Git's REPO and REMOTE stay immediate-select.

The earlier opt-in Git test buttons were retired after the operator confirmed
that continuously changing the real branch/repository context while dragging
is an essential navigation workflow. Historical pilot evidence lives in PRs.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
slider = (ROOT / "components/SelectorSlider.qml").read_text(encoding="utf-8")
hospital = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")

# Only the temporary Git controls are removed; the shared mechanic survives.
for removed in (
    "sliderIndexLabOpen", "sliderIndexLabToggle", "sliderIndexLabLoader",
    "repoIndexPilotEnabled", "repoIndexPilotToggle",
    "remoteIndexPilotEnabled", "remoteIndexPilotToggle",
    "LIVE REPO //", "LIVE REMOTE //", "INDEX LAB //",
    "SelectorSliderIndexPilot.qml",
):
    assert removed not in git, removed

repo = git.split("id: repoSlider", 1)[1].split("id: remoteSlider", 1)[0]
remote = git.split("id: remoteSlider", 1)[1].split("onIndexRequested:", 1)[1]
assert "indexInteraction:" not in repo
assert "indexInteraction:" not in remote
assert "gitService.selectRepo(index);" in repo
assert "gitService.selectRemote(index);" in remote
assert 'root.targetMatchSource = "remote";' in remote
assert "root.remoteActivityPoints()" in git

# The shared component retains the optional preview-release capability;
# Git instances intentionally inherit the original legacy default.
assert 'property string indexInteraction: "legacy"' in slider
assert 'property bool previewGestureActive: false' in slider
assert "stabilizeLegacyRelease" not in slider

# Hospital's one approved temporary control and opt-in are still present.
floor = hospital.split("id: floorSlider", 1)[1].split("onIndexRequested:", 1)[0]
assert "indexInteraction: root.floorIndexPilotEnabled" in floor
assert "LIVE FLOOR // OFF" in hospital
assert "LIVE FLOOR // ON" in hospital

print("SELECTOR INDEX // GIT LEGACY DEFAULT / PILOT BUTTONS RETIRED // PASS")
