#!/usr/bin/env python3
"""Regression contracts for independent, extensible Main Mode content-glow planes.

This checks the QML ownership/stacking architecture and opt-in host contract,
not actual GPU pixel rendering or driver transform fidelity.
"""
from pathlib import Path
r = Path(__file__).resolve().parents[2]
mode = (r / "components/ModeButton.qml").read_text(encoding="utf-8")
base = (r / "components/DockButton.qml").read_text(encoding="utf-8")
safe = (r / "components/SafeDropShadow.qml").read_text(encoding="utf-8")
hash_glow = (r / "components/TextHashGlow.qml").read_text(encoding="utf-8")
cpu = (r / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")

assert "default property alias contentData: customContentHost.data" in mode
assert "property Item primaryGlowHost: null" in mode
assert "property Item labelGlowHost: null" in mode
assert "readonly property Item contentEffectPlane: contentLayer" in mode
assert "readonly property Item effectivePrimaryGlowHost:" in mode
assert "readonly property Item effectiveLabelGlowHost:" in mode
assert "validGlowHost(primaryGlowHost, primaryGlowSource)" in mode
assert "validGlowHost(labelGlowHost, labelGlowSource)" in mode
assert "ancestor === sourceItem" in mode
assert "ancestor = ancestor.parent;" in mode
assert "sourceItem.Window.window !== candidate.Window.window" in mode
assert "id: contentLayer" in mode
assert "anchors.fill: parent\n        z: 0" in mode
assert "parent: modeButton.effectivePrimaryGlowHost" in mode
assert "parent: modeButton.effectiveLabelGlowHost" in mode
assert "safeSource: modeButton.primaryGlowSource" in mode
assert "safeSource: modeButton.labelGlowSource" in mode
assert "ModeButtonWideHalo {" in mode and "ModeButtonCloseHalo {" in mode
assert "id: contentLayer" in base and "z: 0" in base
assert "source: sourceAttached ? safeSource : null" in safe
assert "sourceAttached && parent !== null" in hash_glow

# A structural brace parser verifies both sampled shadows are declared INSIDE
# a dedicated content/effect plane, never as root siblings above the front halo.
def block_end(source, start):
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise AssertionError("unbalanced QML block")

start = mode.index("Item {\n        id: contentLayer")
end = block_end(mode, start)
plane = mode[start:end]
assert plane.count("TextHashGlow {") == 2
assert plane.count("id: customContentHost") == 1
assert plane.count("id: defaultContentHost") == 1
assert mode[:start].count("TextHashGlow {") == 0
assert mode[end:].count("TextHashGlow {") == 0
assert "z: 0" in plane
assert "scale:" in cpu and "customPrimaryGlowSource: textModeIcon" in cpu
assert "TextHashGlow {" not in cpu[cpu.index("id: modeButton"):cpu.index("// TWO-BODY MONITOR ADAPTER")]
print("ModeButton independent glow plane contracts: PASS")
