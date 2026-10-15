#!/usr/bin/env python3
"""Projects visual/geometry source contracts.

Source-only checks: real GohuFont, clipping, scrollbar and QML pointer behavior
still require inspection on the operator's running Quickshell.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
board = (root / "widgets/GitHubProjectsView.qml").read_text(encoding="utf-8")
table = (root / "widgets/GitHubProjectsTableView.qml").read_text(encoding="utf-8")
roadmap = (root / "widgets/GitHubProjectsRoadmapView.qml").read_text(encoding="utf-8")

# Exact requested semantic color accents on the production Projects screen.
for name, color in (
    ("WORK", "orange"), ("ISSUE", "red"), ("PR", "green"),
    ("< PROJECT", "orange"), ("PROJECT >", "orange"),
):
    assert (
        f'label: "{name}"\n'
        f'                            accentColor: Colors.{color}\n'
        f'                            preserveIdentity: true'
    ) in board, name
assert '"PROJECT INDEX // "' in board
index_title = board.split('"PROJECT INDEX // "', 1)[1].split("ActionButton {", 1)[0]
assert "color: Colors.magenta" in index_title

# All entry text/placeholder magenta; caret orange; only context border orange.
input_component = board.split("component ProjectInput: Rectangle {", 1)[1].split(
    "Connections {", 1
)[0]
assert "property color accentColor: Colors.magenta" in input_component
assert "border.color: field.accentColor" in input_component
assert "color: Colors.magenta" in input_component
assert "cursorDelegate: Rectangle {" in input_component
assert "color: Colors.orange" in input_component
assert "selectionColor: Colors.magenta" in input_component
assert 'id: itemBodyInput\n                            accentColor: Colors.orange' in board
assert 'placeholderText: "NEW PROJECT TITLE"' in board
assert '"NEW WORK ITEM"' in board

# Existing second-row geometry used width - 190, but requires
# 34 + 106 + 34 + three 8px gaps = 198px.
assert "width: Math.max(0, parent.width - 198)" in board
assert "width: Math.max(0, mapScroll.width - 20)" in board
assert "width: parent.width - 190" not in board

# Prefer Syntagma's U+00D7 Remove and the shared destructive ActionButton,
# retaining the two-stage confirmation and actual service behavior.
for name, view, count in (
    ("board", board, 1), ("table", table, 1), ("roadmap", roadmap, 2)
):
    assert view.count("Components.ActionButton {") == count, name
    assert view.count("destructive: true") == count, name
    assert view.count('? "⚠︎"') == count, name
    assert view.count(': "×"') == count, name
    assert view.count("selectedForegroundColor: Colors.red") == count, name
    assert view.count("selectedBorderColor: Colors.red") == count, name
    assert view.count("onTriggered:") >= count, name
    assert "font.pixelSize: 7" not in view, name
    assert "font.pixelSize: 8" not in view, name

assert 'height: 20' in board
assert 'height: 26' in table
assert roadmap.count('Components.ActionButton {\n') == 2

# The two star rails are reparented outside their positioned Columns. An
# opaque mapToItem() call alone does not declare reactive x/y dependencies,
# so the rail can remain at an initial pre-layout location (too high/left).
# Each rail must explicitly follow its viewport's current Column offset.
for flickable in ("projectList", "mapScroll"):
    rail = board.split(
        f"NeonScrollBar {{\n                        flickable: {flickable}", 1
    )[1].split("visible:", 1)[0]
    assert f"mountingParent: {flickable}.parent.parent" in rail
    assert f"x: {flickable}.parent.x + {flickable}.x" in rail
    assert f"+ {flickable}.width - width - rightInset" in rail
    assert f"y: {flickable}.parent.y + {flickable}.y + effectiveTopInset" in rail
    assert "mapToItem(" not in rail.split("mountingParent:", 1)[1]

# Keep existing clearance rather than sliding cards back under the star rail.
assert "width: Math.max(0, mapScroll.width - 20)" in board

print("GITHUB PROJECTS // VISUAL GRAMMAR AND ARROW GEOMETRY PASS")
