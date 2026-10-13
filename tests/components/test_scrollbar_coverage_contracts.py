#!/usr/bin/env python3
"""Static coverage gate for shared scroll indicators (Nurse 3r / Syntagma).

This verifies source presence and star-family adoption, NOT the actual visual
appearance, content clearance or interaction during Quickshell execution.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
WIDGETS = ROOT / "widgets"

SCROLLABLE = re.compile(r"\b(?:Flickable|ListView|GridView)\s*\{")
SHARED = re.compile(r"\bNeonScrollBar\s*\{")
STARS = re.compile(r'\bhandleStyle\s*:\s*"star"')

# Existing rich/custom rails have their own position indicators and semantics.
# A separate review is needed before replacing them with NeonScrollBar stars.
RICH_RAIL_SHORTFALL = {
    "widgets/GitBranchesView.qml": 1,  # branchStripRail
    "widgets/GitW.qml": 2,             # ScrollingStatusValue and localTargetScrollRail
}

checked = 0
for path in sorted(WIDGETS.rglob("*.qml")):
    source = path.read_text(encoding="utf-8")
    relative = str(path.relative_to(ROOT))
    scroll_count = len(SCROLLABLE.findall(source))
    if not scroll_count:
        continue
    checked += 1
    bar_count = len(SHARED.findall(source))
    allowance = RICH_RAIL_SHORTFALL.get(relative, 0)
    assert bar_count + allowance >= scroll_count, (
        f"{relative}: {scroll_count} scrollable areas, but only {bar_count} "
        f"shared indicators + {allowance} documented rich rails"
    )
    if path.name.startswith(("Git", "Hospital")):
        assert len(STARS.findall(source)) >= bar_count, (
            f"{relative}: Git/Hospital shared scrollbars must default to stars"
        )

for name, expected_style in (
    ("components/BranchMap.qml", '"star"'),
    ("components/ConversationFeed.qml", "chatFeed.scrollHandleStyle"),
):
    source = (ROOT / name).read_text(encoding="utf-8")
    assert SHARED.search(source), f"{name}: scroll indicator missing"
    assert f"handleStyle: {expected_style}" in source, (
        f"{name}: scrollbar handle style mismatch"
    )

room_chat = (ROOT / "widgets/HospitalRoomChatView.qml").read_text(encoding="utf-8")
assert 'scrollHandleStyle: "star"' in room_chat, "Hospital conversation star override missing"

for name in (
    "widgets/RepositoryProfileView.qml",
    "widgets/WorkflowLibraryView.qml",
    "widgets/GitHubWorkItemsView.qml",
):
    source = (ROOT / name).read_text(encoding="utf-8")
    assert "handleGlowEnabled: true" in source, (
        f"{name}: previously non-glowing scrollbar handle not restored"
    )

print(f"Scrollbar coverage source check: PASS ({checked} scrollable widget files)")
