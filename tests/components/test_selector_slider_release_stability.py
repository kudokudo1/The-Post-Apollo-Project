#!/usr/bin/env python3
"""Source-contract guard for Git REMOTE's legacy release-flick hotfix.

This checks scoping/invariants, NOT actual Qt animation or operator experience.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
slider = (ROOT / "components/SelectorSlider.qml").read_text(encoding="utf-8")
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
hospital = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")

# All sliders preserve the old behavior unless explicitly opted in.
assert "property bool stabilizeLegacyRelease: false" in slider
assert "property string indexInteraction: \"legacy\"" in slider
assert "const invalid = count <= 1" in slider
assert "currentIndex < 0 || currentIndex >= count" in slider
assert "return handleTravel() * stableLegacyFraction" in slider
assert "legacyReleaseTimer.restart();" in slider
assert "Component.onCompleted: cacheLegacyFraction()" in slider

# PREVIEW mode stays separated; REMOTE alone opts in to the grace window.
assert "y: slider.indexPilot" in slider
assert "stabilizeLegacyRelease: true" in git
assert git.count("stabilizeLegacyRelease: true") == 1
assert "indexInteraction: root.remoteIndexPilotEnabled" in git

repo_block = git.split("id: repoSlider", 1)[1].split("id: remoteSlider", 1)[0]
remote_block = git.split("id: remoteSlider", 1)[1].split("id: sliderIndexLabToggle", 1)[0]
assert "stabilizeLegacyRelease" not in repo_block
assert "stabilizeLegacyRelease: true" in remote_block
assert "gitService.selectRemote(index);" in remote_block
assert "gitService.selectRepo(index);" in repo_block

# Hospital uses the shared component but no opt-in: untouched floor behavior.
floor_block = hospital.split("id: floorSlider", 1)[1].split("onIndexRequested:", 1)[0]
assert "stabilizeLegacyRelease" not in floor_block

# The selector is not being changed to fake selection or external activity.
assert "indexRequested(finalIndex)" in slider
assert "activityPoints" in slider
print("SELECTOR LEGACY RELEASE // REMOTE-ONLY STATIC CONTRACT PASS")
