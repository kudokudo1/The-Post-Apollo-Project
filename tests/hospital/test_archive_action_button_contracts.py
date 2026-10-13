#!/usr/bin/env python3
"""Structural contracts for the Syntagma Hospital Archive ActionButton pilot.

The source and attention filter rows are selectors, not migrated actions.
The OPEN, FAVORITE, and EXPORT actions use the shared ActionButton.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = (ROOT / "widgets/HospitalArchiveView.qml").read_text(encoding="utf-8")
SHARED = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")

assert "component ArchiveActionButton: ActionButton {" in ARCHIVE
assert "default property alias contentData: contentHost.data" in SHARED

# Only three ordinary actions were migrated. Both selector families stay local.
assert ARCHIVE.count("\n                        ArchiveActionButton {") == 3
assert ARCHIVE.count("\n                ArchiveButton {") == 2
assert "root.sourceFilter === modelData" in ARCHIVE
assert "root.attentionFilter === modelData" in ARCHIVE
assert "component ArchiveButton: Rectangle {" in ARCHIVE

for marker in (
    "height: 35",
    "implicitHeight: 35",
    "Accessible.role: Accessible.Button",
    "Accessible.name: actionDescription",
    "contentItem.clip: true",
    "minimumLabelMeasure.implicitWidth <= contentWidthBudget",
    "compactIconMeasure.implicitWidth <= contentWidthBudget",
    "fontSizeMode: Text.HorizontalFit",
    "elide: Text.ElideNone",
    "contentGlowIdleOpacity: 0.35",
    "contentGlowHoverOpacity: 0.75",
    "contentGlowPressedOpacity: 1.0",
    "softGlowIdleOpacity: 0.25",
    "softGlowHoverOpacity: 0.55",
    "softGlowPressedOpacity: 0.60",
    "wideGlowEnabled: false",
    "actionWidth: Math.max(",
    "(width - 2 * spacing) / 3",
    "root.selectedEvent !== null",
    "root.filteredEvents.length > 0",
    "parent.height - 163",
):
    assert marker in ARCHIVE, marker

# The three callbacks must remain connected to their live owners.
for marker in (
    'fullLabel: "OPEN"',
    "root.eventActivated(",
    '"UNFAVORITE"',
    '"FAVORITE"',
    "isPinned(root.selectedEvent)",
    ".togglePinned(",
    'fullLabel: "EXPORT"',
    ".exportArchive(",
    "root.filterLabel()",
):
    assert marker in ARCHIVE, marker

# Semantically colored Favorite and Export are not destructive operations.
assert "accentColor: Colors.yellow" in ARCHIVE
assert "accentColor: Colors.green" in ARCHIVE
assert ARCHIVE.count("specialAction: true") == 2
assert "destructive: true" not in ARCHIVE

print("Hospital Archive Action Button pilot contracts: PASS")
