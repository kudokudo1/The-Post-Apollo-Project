#!/usr/bin/env python3
"""CPU++ sampled-text glow lifecycle and icon/caption isolation contracts.

Static checks only: Qt/Wayland/NVIDIA rendering still needs an operator
observation. These controls must not change the shared glow component.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
cpu = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
mode = (ROOT / "components/ModeButton.qml").read_text(encoding="utf-8")
safe = (ROOT / "components/SafeDropShadow.qml").read_text(encoding="utf-8")

for token in (
    'Quickshell.env("POST_APOLLO_CPU_GLOW_TEST")',
    "readonly property string glowStartupChoice:",
    "property int modeGlowExperiment:",
    'glowStartupChoice === "C" ? 3',
    'glowStartupChoice === "D" ? 4',
    'glowStartupChoice === "E" ? 5',
    ": 0",

    "id: sampledGlowTestControls",
    'text: "GLOW TEST //"',
    'label: "BASE"',
    'label: "A / OFF"',
    'label: "B / REATTACH"',
    'label: "C / ICON"',
    'label: "D / LABEL"',
    'label: "E / FIXED"',
    "onClicked: cpuPlusWindow.modeGlowExperiment = modelData.value",
    "readonly property bool sampledTextActive:",
    "cpuPlusWindow.modeGlowExperiment !== 1",
    "cpuPlusWindow.modeGlowExperiment !== 2",
    "|| cpuPlusWindow.menuOpen",
    "readonly property bool sampledPrimaryActive:",
    "readonly property bool sampledCaptionActive:",
    "cpuPlusWindow.modeGlowExperiment !== 3",
    "cpuPlusWindow.modeGlowExperiment !== 4",
    "sampledPrimaryActive ? textModeIcon : null",
    "sampledCaptionActive ? modeCaption : null",
    'sampledPrimaryActive && modelData.kind !== "thermal"',
    "labelGlowEnabled: sampledCaptionActive",
    "cpuPlusWindow.modeGlowExperiment === 5",
    "? 1.0",
):
    assert token in cpu, f"CPU++ isolation diagnostic missing: {token}"

# Confirm the cold-start choice is bound before any ModeButton delegate is
# instantiated; runtime-only button clicks cannot prove cold-start isolation.
assert cpu.index('Quickshell.env("POST_APOLLO_CPU_GLOW_TEST")') < cpu.index("model: cpuPlusWindow.modes")
assert "property int modeGlowExperiment: 0" not in cpu

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
print("CPU++ sampled-text glow A/B/C/D/E isolation diagnostics: PASS")
