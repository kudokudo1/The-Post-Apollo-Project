#!/usr/bin/env python3
"""Prevent the ON-mode handle snapping to stale owner state on mouse release.

Static source contract only. It does not replace actual Qt pointer/visual tests.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
slider = (ROOT / "components/SelectorSlider.qml").read_text(encoding="utf-8")
git = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
hospital = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")

# ON-mode preview is explicit gesture state, NOT MouseArea.pressed:
# Qt may clear pressed before onReleased sends the owner's selection request.
assert "property bool previewGestureActive: false" in slider
preview_definition = slider.split("readonly property bool previewActive:", 1)[1].split("\n\n", 1)[0]
assert "previewGestureActive" in preview_definition
assert "dragArea.pressed" not in preview_definition

# The interaction starts after preview position/index is captured.
press = slider.split("onPressed: function(mouse) {", 1)[1].split("onPositionChanged: function(mouse) {", 1)[0]
assert press.index("slider.previewIndex = index;") < press.index(
    "slider.previewGestureActive = true;"
)

# On release, the owner is asked BEFORE the preview latch drops.
release = slider.split("onReleased: {", 1)[1].split("onCanceled: {", 1)[0]
assert release.index("slider.indexRequested(finalIndex);") < release.index(
    "slider.previewGestureActive = false;"
)

# Cancellation and toggling back to legacy always leave no stale preview.
cancel = slider.split("function cancelIndexPreview()", 1)[1].split(
    "onIndexInteractionChanged:", 1
)[0]
assert "previewGestureActive = false;" in cancel
assert "onIndexInteractionChanged:" in slider
assert "if (!indexPilot)" in slider

# The previous speculative OFF-mode fix is completely absent.
assert "stabilizeLegacyRelease" not in slider
assert "legacyReleaseGrace" not in slider
assert "stabilizeLegacyRelease" not in git
assert "property string indexInteraction: \"legacy\"" in slider

# Only REMOTE opts into new mechanics; REPO and Hospital remain legacy.
repo_block = git.split("id: repoSlider", 1)[1].split("id: remoteSlider", 1)[0]
remote_block = git.split("id: remoteSlider", 1)[1].split(
    "id: sliderIndexLabToggle", 1
)[0]
floor_block = hospital.split("id: floorSlider", 1)[1].split(
    "onIndexRequested:", 1
)[0]
assert "indexInteraction:" not in repo_block
assert "indexInteraction: root.remoteIndexPilotEnabled" in remote_block
assert "gitService.selectRemote(index);" in remote_block
assert "indexInteraction:" not in floor_block

print("SELECTOR INDEX // ON RELEASE LATCH STATIC CONTRACT PASS")
