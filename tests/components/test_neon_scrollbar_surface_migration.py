#!/usr/bin/env python3
"""Source-level migration assertions, not a live Quickshell visual certification."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

STAR_FAMILY = [
    "widgets/GitW.qml",
    "widgets/GitBlameView.qml",
    "widgets/GitBranchesView.qml",
    "widgets/GitChangesView.qml",
    "widgets/GitConflictEditorView.qml",
    "widgets/GitHistoryView.qml",
    "widgets/GitRepositoryView.qml",
    "widgets/GitHubIssueControlView.qml",
    "widgets/GitHubProjectsView.qml",
    "widgets/GitHubProjectsTableView.qml",
    "widgets/GitHubProjectsRoadmapView.qml",
    "widgets/GitHubPullRequestControlView.qml",
    "widgets/GitHubWorkItemsView.qml",
    "widgets/GitHistoryAbsorbView.qml",
    "widgets/GitHistorySurgeryView.qml",
    "widgets/GitHistorySplitView.qml",
    "widgets/GitHistorySplitHunkView.qml",
    "widgets/GitHistorySplitLineView.qml",
    "widgets/GitInteractiveRebaseView.qml",
    "widgets/GitInteractiveRebaseSessionView.qml",
    "widgets/GitChangeTransferView.qml",
    "widgets/GitLineTransferView.qml",
    "widgets/GitOperationsView.qml",
    "widgets/HospitalW.qml",
    "widgets/HospitalArchiveView.qml",
    "widgets/HospitalAssignmentsView.qml",
    "widgets/HospitalChartSuggestionsView.qml",
    "widgets/HospitalChartsView.qml",
    "widgets/HospitalGitHubAttentionView.qml",
    "widgets/HospitalGitHubMergeQueueView.qml",
    "widgets/HospitalIntercomMenu.qml",
    "widgets/HospitalPhoneMenu.qml",
    "widgets/HospitalReceptionistView.qml",
    "widgets/HospitalReportsView.qml",
    "widgets/HospitalRoomReportsView.qml",
    "widgets/HospitalRoundsView.qml",
    "widgets/HospitalSpecialistsView.qml",
    "widgets/RepositoryProfileView.qml",
    "widgets/WorkflowLibraryView.qml",
    "widgets/RunInspectorDrawer.qml",
]

def source(path):
    return (ROOT / path).read_text(encoding="utf-8")

starred_instances = 0
for file_path in STAR_FAMILY:
    content = source(file_path)
    blocks = re.findall(r"\bNeonScrollBar\s*\{([^{}]*)\}", content)
    assert blocks, f"{file_path}: expected at least one scrollbar"
    for block in blocks:
        assert 'handleStyle: "star"' in block, f"{file_path}: scrollbar is not a star"
    starred_instances += len(blocks)

for file_path in [
    "widgets/GitHubWorkItemsView.qml",
    "widgets/WorkflowLibraryView.qml",
    "widgets/RepositoryProfileView.qml",
    "widgets/appcontrol/TaskManagerView.qml",
    "widgets/notifications/NotificationsHubW.qml",
]:
    content = source(file_path)
    assert "railGlowEnabled: true" in content, f"{file_path}: rail glow missing"
    assert "handleGlowEnabled: false" not in content, f"{file_path}: handle glow disabled"

shared = source("components/NeonScrollBar.qml")
assert "property Item mountingParent: null" in shared
assert "flickable.mapToItem(mountingParent, 0, 0)" in shared
assert "property color railGlowColor: railColor" in shared

assert 'property string scrollbarHandleStyle: "bar"' in source("components/ConversationFeed.qml")
assert 'scrollbarHandleStyle: "star"' in source("widgets/HospitalRoomChatView.qml")
assert "flickable: suggestionDetailScroll" in source("widgets/HospitalChartsView.qml")

# Inventory all source-declared Flickable/ListView/GridView widget panes.
# Specialized existing indicators remain explicit, source-audited exceptions.
# This is a structural census, NOT proof of rendered geometry or Qt hit targets.
SPECIALIZED_SCROLL_TRACKS = {
    "widgets/AppControlW.qml": 3,         # Results, resource scope, detail
    "widgets/GitBranchesView.qml": 1,     # Existing horizontal branch strip
    "widgets/GitW.qml": 1,                # Tiny horizontal status-value rail
}
all_scroll_targets = 0
all_neon_bars = 0
for path in (ROOT / "widgets").rglob("*.qml"):
    rel = path.relative_to(ROOT).as_posix()
    content = path.read_text(encoding="utf-8")
    targets = len(re.findall(r"\\b(?:Flickable|ListView|GridView)\\s*\\{", content))
    bars = len(re.findall(r"\\bNeonScrollBar\\s*\\{", content))
    exceptions = SPECIALIZED_SCROLL_TRACKS.get(rel, 0)
    assert targets <= bars + exceptions, (
        f"{rel}: {targets} scrollable panes but only {bars} NeonScrollBar "
        f"instances + {exceptions} explicitly reviewed custom indicators"
    )
    all_scroll_targets += targets
    all_neon_bars += bars

for rel in ("components/BranchMap.qml", "components/ConversationFeed.qml"):
    content = source(rel)
    assert len(re.findall(r"\\bNeonScrollBar\\s*\\{", content)) >= len(
        re.findall(r"\\b(?:Flickable|ListView|GridView)\\s*\\{", content)
    ), f"{rel}: shared scroll pane without an indicator"

print(
    f"Scrollbar surface migration contracts: PASS "
    f"({starred_instances} Git/Hospital stars; "
    f"{all_scroll_targets} widget scroll panes; {all_neon_bars} shared bars; "
    f"{sum(SPECIALIZED_SCROLL_TRACKS.values())} bespoke exceptions)"
)
