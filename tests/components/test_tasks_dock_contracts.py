#!/usr/bin/env python3
"""TASKS dock click and basic menu integration contract; no task backend yet."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
TASKS = (ROOT / "modules/Tasks.qml").read_text(encoding="utf-8")

# Preserve the existing left-side module order. TASKS comes immediately after Git.
LEFT = SHELL.split("// ===== LEFT MODULES", 1)[1].split("// ===== CENTER MODULE", 1)[0]
assert LEFT.count("            Git {") == 1
assert LEFT.count("            Tasks {") == 1
assert LEFT.count("            TasksW {") == 1
assert LEFT.index("        // Git") < LEFT.index("            Git {") < LEFT.index("        // Tasks") < LEFT.index("            Tasks {")
assert "menuOpen: tasksWindow.menuOpen" in LEFT
assert "onToggleRequested: tasksWindow.toggle()" in LEFT
assert "dockCenterX: shellRoot.margins.left + leftModules.x" in LEFT
assert "+ tasksHost.x + tasksButton.width / 2" in LEFT
assert "chassisTopY: hospitalWindow.panelTopMargin" in LEFT

# Use the existing dock foundation, not a duplicate shadow or click layer.
assert "DockButton {" in TASKS
assert 'import "../components"' in TASKS
assert "implicitHeight: 50" in TASKS
assert "implicitWidth: Math.max(72, Math.ceil(tasksMark.implicitWidth) + 20)" in TASKS
assert "interactive: false" not in TASKS
assert "property bool menuOpen: false" in TASKS
assert "signal toggleRequested()" in TASKS
assert "open: menuOpen" in TASKS
assert "onLeftClicked: toggleRequested()" in TASKS
assert "contentGlowSource: tasksMark" in TASKS
for state in ("normal", "hover", "pressed"):
    assert f"{state}ContentGlowColor: Colors.cyan" in TASKS
    assert f"{state}DockGlowColor: Colors.cyan" in TASKS
# All artwork, including combining stars, is one tintable text run.
# The entire glyph cluster follows menu state, independent of hover.
assert 'text: "݁˖✎๋࣭🗒︎๋࣭⊹"' in TASKS
assert "textFormat: Text.PlainText" in TASKS
assert "color: tasksDock.menuOpen ? Colors.magenta : Colors.white" in TASKS
assert "Colors.yellow" not in TASKS
assert "<font" not in TASKS
for forbidden in ("MouseArea {", "SafeDropShadow {", "RectangularShadow {", "Process {", "TasksW {"):
    assert forbidden not in TASKS, forbidden

print("TASKS dock integration contracts: PASS")
