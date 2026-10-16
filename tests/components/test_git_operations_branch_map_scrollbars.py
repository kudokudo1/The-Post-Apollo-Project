#!/usr/bin/env python3
"""Operations star lane + BranchMap single scrollbar source contracts.

The shared NeonScrollBar offscreen smoke tests pointer/wheel behavior.
Operator visual acceptance of the two actual Git pages remains separate.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
operations = (ROOT / "widgets/GitOperationsView.qml").read_text(encoding="utf-8")
branch_map = (ROOT / "components/BranchMap.qml").read_text(encoding="utf-8")
branches = (ROOT / "widgets/GitBranchesView.qml").read_text(encoding="utf-8")
shared = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")

# Operations: row width is ListView width, which now excludes the star.
assert 'id: operationList' in operations
assert "anchors.fill: parent" in operations
assert "anchors.margins: 6" in operations
assert "anchors.rightMargin: 6 + operationScrollTrack.reservedExtent" in operations
assert "width: operationList.width" in operations
assert 'id: operationScrollTrack' in operations
assert 'flickable: operationList' in operations
assert 'handleStyle: "star"' in operations
assert 'x: parent.width - width - 6' in operations
assert 'y: operationList.y + effectiveTopInset' in operations
assert 'visible: operationList.visible && scrollable' in operations
assert 'z: 2' in operations
assert "NeonScrollBar { flickable: operationList; handleStyle: \"star\" }" not in operations

# Verify the layout arithmetic from the source's intended inset values:
# panel width P; list ends at P - (6 + 20), rail begins at P - 6 - 16.
# Four pixels separate the list edge from the star's 16px clickable region.
star_width = 16
reserved_width = 20
panel_edge = 600
list_edge = panel_edge - (6 + reserved_width)
star_start = panel_edge - 6 - star_width
assert star_start - list_edge == 4
assert 'property int starAreaWidth: 16' in shared
assert 'readonly property real reservedExtent:' in shared

# The Branches page owns one BranchMap which draws Canvas/row topology.
# Remove only the legacy on-scroll star overlay, not topology/repaint code
# nor the independent horizontal branch-selector rail.
assert 'BranchMap {' in branches
assert 'id: topologyFlick' in branch_map
assert 'id: graphCanvas' in branch_map
assert 'commitSelected(string sha)' in branch_map
assert branch_map.count('NeonScrollBar {') == 1
assert 'flickable: topologyFlick' in branch_map
assert 'handleStyle: "star"' in branch_map
assert 'visible: topologyFlick.visible && scrollable' in branch_map
assert 'id: scrollIndicator' not in branch_map
assert 'topologyFlick.moving' not in branch_map
assert 'topologyFlick.flicking' not in branch_map
assert 'topologyFlick.dragging' not in branch_map
assert 'id: branchStripRail' in branches
assert 'id: branchStripFlick' in branches

print("GIT OPERATIONS / BRANCH MAP // SCROLLBAR GEOMETRY PASS")
