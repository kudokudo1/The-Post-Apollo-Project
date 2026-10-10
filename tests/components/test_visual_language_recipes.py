#!/usr/bin/env python3
"""First-pass static contracts: additive, semantic visual recipes."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "components"
QMLDIR = (COMP / "qmldir").read_text(encoding="utf-8")


def content(filename):
    return (COMP / filename).read_text(encoding="utf-8")


names = (
    "VisualLanguage",
    "HaloGlow",
    "ModeButtonCloseHalo",
    "ModeButtonWideHalo",
    "ActionButtonHalo",
    "ChassisGlow",
    "TextHashGlow",
    "QuietText",
    "SecondaryText",
)
for name in names:
    assert f"{name} 1.0 {name}.qml" in QMLDIR, name

tokens = content("VisualLanguage.qml")
for expected in (
    "modeCloseSpread: 3",
    "modeCloseActiveOpacity: 0.50",
    "modeWideSpread: 10",
    "modeWideActiveOpacity: 0.09",
    "chassisCloseSpread: 6",
    "chassisCloseOpacity: 0.21",
    "chassisWideSpread: 12",
    "chassisWideOpacity: 0.05",
    "textHashSamples: 9",
    "quietTextOpacity: 0.42",
    "secondaryTextOpacity: 0.68",
):
    assert expected in tokens, expected

close = content("ModeButtonCloseHalo.qml")
wide = content("ModeButtonWideHalo.qml")
for part in (close, wide):
    for flag in ("selected", "hovered", "keyboardSelected", "pressed"):
        assert f"property bool {flag}:" in part
    assert "color: VisualLanguage.modeHaloColor" in part
    assert "HaloGlow {" in part

assert "z: -1" in close and "z: 1" in wide
assert "VisualLanguage.modeCloseSpread" in close
assert "VisualLanguage.modeWideSpread" in wide

chassis = content("ChassisGlow.qml")
assert chassis.count("HaloGlow {") == 2
assert "z: -1" in chassis and "z: -2" in chassis
assert "VisualLanguage.chassisCloseOpacity" in chassis
assert "VisualLanguage.chassisWideOpacity" in chassis

hash_glow = content("TextHashGlow.qml")
assert "SafeDropShadow {" in hash_glow
assert "foregroundColor === Colors.magenta" in hash_glow
assert "? Colors.magenta : preferredGlowColor" in hash_glow
assert "safeSource.mapToItem(parent, 0, 0)" in hash_glow
assert "VisualLanguage.textHashSamples" in hash_glow
assert "DropShadow {" not in hash_glow.replace("SafeDropShadow {", "")

for name, token in (("QuietText", "quietTextOpacity"),
                    ("SecondaryText", "secondaryTextOpacity")):
    source = content(f"{name}.qml")
    assert "GohuText {" in source
    assert f"VisualLanguage.{token}" in source
    assert "MouseArea {" not in source
    assert "DropShadow {" not in source

for template in ("ModeButton", "ChassisGlow", "TextRoles"):
    assert content(f"{template}.qml.template")
assert "ModeButtonWideHalo {" in content("ModeButton.qml.template")
assert "safeSource: primary" in content("TextRoles.qml.template")

for name in names:
    source = content(f"{name}.qml")
    for forbidden in ("PanelWindow {", "MouseArea {", "WlrLayershell",
                      "Process {", "Keys.on"):
        assert forbidden not in source, (name, forbidden)

print("Visual language semantic recipe contracts: PASS")
