#!/usr/bin/env python3
"""FinanceW launcher-only source contract (no menu, provider, or local writes)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
FINANCE = (ROOT / "modules/Finance.qml").read_text(encoding="utf-8")

# A direct default DockButton between the media player and Hospital.
assert "Mediaplayer {}\n\n        // Finance\n\n        Finance {}\n\n        // Hospital" in SHELL
assert SHELL.count("        Finance {}") == 1
assert "DockButton {" in FINANCE
assert 'import "../components"' in FINANCE

# Do not normalize the operator's decorated identity or lose combining marks.
assert 'text: "˗ˋˏ˖<font color=\'" + Colors.green + "\'>⛁⛀</font>๋࣭⭑ˎˊ˗"' in FINANCE
assert "textFormat: Text.StyledText" in FINANCE
assert "implicitWidth: Math.max(80, Math.ceil(financeMark.implicitWidth) + 24)" in FINANCE
assert "contentGlowSource: financeMark" in FINANCE
assert "color: financeDock.foregroundColor" in FINANCE
assert "⛀⛁ ⛁⛀" not in FINANCE

# Only the coins use sub-Omnitrix green; decorations remain white.
for state in ("normal", "hover", "pressed", "open"):
    assert f"{state}ForegroundColor: Colors.white" in FINANCE
for state in ("normal", "hover", "pressed"):
    assert f"{state}ContentGlowColor: Colors.omnitrix" in FINANCE
    assert f"{state}DockGlowColor: Colors.omnitrix" in FINANCE
assert "openGlowColor: Colors.omnitrix" in FINANCE

# No backend, menu, custom click policy, or duplicate effect.
for forbidden in (
    "FinanceW {", "Process {", "onLeftClicked:", "onRightClicked:",
    "MouseArea {", "SafeDropShadow {", "RectangularShadow {",
):
    assert forbidden not in FINANCE, forbidden

print("FinanceW launcher-only contract: PASS")
