#!/usr/bin/env python3
"""CPU++ A/B sampled-text glow lifecycle diagnostic contracts.

Static checks only: Qt/Wayland/NVIDIA rendering still needs an operator
observation. These controls must not change the shared glow component.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
cpu = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
mode = (ROOT / "components/ModeButton.qml").read_text(encoding="utf-8")
safe = (ROOT / "components/SafeDropShadow.qml").read_text(encoding="utf-8")

for token in (
    "property int modeGlowExperiment: 0",
    "id: sampledGlowTestControls",
    'text: "GLOW TEST //"',
    'label: "BASE"',
    'label: "A / OFF"',
    'label: "B / REATTACH"',
    "onClicked: cpuPlusWindow.modeGlowExperiment = modelData.value",
    "readonly property bool sampledTextActive:",
    "cpuPlusWindow.modeGlowExperiment !== 1",
    "cpuPlusWindow.modeGlowExperiment !== 2",
    "|| cpuPlusWindow.menuOpen",
    "sampledTextActive ? textModeIcon : null",
    "sampledTextActive ? modeCaption : null",
    'sampledTextActive && modelData.kind !== "thermal"',
    "labelGlowEnabled: sampledTextActive",
):
    assert token in cpu, f"CPU++ A/B diagnostic missing: {token}"

# Deliberately retain main-mode scale, semantic switching, thermal icon
# effect and close/reopen visibility behavior throughout the experiment.
for token in (
    "visible: menuOpen",
    "onTriggered:",
    "cpuPlusWindow.selectMode(index);",
    "duration: 90",
    "Easing.OutQuad",
    "sourceComponent:",
    "item.glowOpacity = 0.46;",
    "selected: index === cpuPlusWindow.selectedModeIndex",
):
    assert token in cpu, f"CPU++ control was disturbed: {token}"

assert 'customPrimaryGlowSource:' in cpu
assert 'customLabelGlowSource:' in cpu
assert 'SafeDropShadow {' in mode or "TextHashGlow {" in mode
assert "source: sourceAttached ? safeSource : null" in safe
print("CPU++ A/B sampled-text glow diagnostics: PASS")
