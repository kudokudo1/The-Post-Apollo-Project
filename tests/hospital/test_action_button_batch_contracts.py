#!/usr/bin/env python3
"""Syntagma // Hospital ordinary ActionButton batch migration contracts.

These contracts protect the boundary between ordinary actions and selector
families, plus command ownership and compact-row safety constraints.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = (ROOT / "components/HospitalActionButton.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")
SHARED = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")

assert "HospitalActionButton 1.0 HospitalActionButton.qml" in QMLDIR
assert "ActionButton {" in ADAPTER
assert "default property alias contentData: contentHost.data" in SHARED
for token in (
    "property bool enabledAction: true",
    "property bool selectedAction: false",
    "available: enabledAction",
    "selected: selectedAction",
    "implicitHeight: 35",
    "contentItem.clip: true",
    "Accessible.role: Accessible.Button",
    "Accessible.name: actionDescription",
    "text: action.fullLabelFits ? action.label",
    "compactIconFits ? action.compactIcon",
    "fontSizeMode: Text.HorizontalFit",
    "contentGlowIdleOpacity: 0.35",
    "contentGlowHoverOpacity: 0.75",
    "contentGlowPressedOpacity: 1.0",
    "softGlowIdleOpacity: 0.25",
    "softGlowHoverOpacity: 0.55",
    "softGlowPressedOpacity: 0.60",
    "wideGlowEnabled: false",
    "pressedFillColor: destructive ? Colors.red : Colors.magenta",
):
    assert token in ADAPTER, token

# Existing ordinary actions only. The original local families continue to
# own filtering/selecting state (and the Rounds/Staff mode filter rows).
views = {
    "HospitalAssignmentsView.qml": (7, 1, "OrderButton"),
    "HospitalChartSuggestionsView.qml": (4, 1, "SuggestionButton"),
    "HospitalChartsView.qml": (9, 4, "ChartButton"),
    "HospitalGitHubAttentionView.qml": (4, 1, "AttnButton"),
    "HospitalGitHubMergeQueueView.qml": (3, 0, "QueueButton"),
    "HospitalRoomReportsView.qml": (4, 0, "ReportButton"),
    "HospitalRoundsView.qml": (2, 2, "RoundsButton"),
    "HospitalSpecialistsView.qml": (1, 3, "StaffButton"),
}
for name, (ordinary_count, selector_count, selector_type) in views.items():
    src = (ROOT / "widgets" / name).read_text(encoding="utf-8")
    assert src.count("\n                HospitalActionButton {") <= ordinary_count
    import re
    actual_actions = re.findall(r"(?m)^\s*HospitalActionButton\s*\{", src)
    actual_selectors = re.findall(rf"(?m)^\s*{selector_type}\s*\{{", src)
    assert len(actual_actions) == ordinary_count, (name, len(actual_actions))
    assert len(actual_selectors) == selector_count, (name, len(actual_selectors))
    assert f"component {selector_type}: Rectangle {{" in src, name

# Explicit semantic boundary: destructive applies only to rejecting a Chart
# suggestion. Close/cancel buttons, source filters, and navigation are not
# automatically destructive.
for name in ("HospitalChartSuggestionsView.qml", "HospitalChartsView.qml"):
    src = (ROOT / "widgets" / name).read_text(encoding="utf-8")
    assert src.count("destructive: true") == 1, name

# Operational callbacks and guard conditions remain owned by their views.
commands = {
    "HospitalAssignmentsView.qml": (
        "assignmentService.startAllReady()",
        'root.openEditor("NEW")',
        'root.openEditor("EDIT")',
        "root.saveEditor()",
    ),
    "HospitalChartSuggestionsView.qml": (
        "chartService.refreshSuggestions()",
        "chartService.promoteSuggestion(",
        "chartService.rejectSuggestion(",
    ),
    "HospitalChartsView.qml": (
        "root.openSuggestionPanel()",
        "chartService.refreshAll()",
        "root.promoteSelectedSuggestion()",
        "root.rejectSelectedSuggestion()",
    ),
    "HospitalGitHubAttentionView.qml": (
        "root.pullRequestRequested(",
        "root.queueRequested(",
        "root.refresh()",
    ),
    "HospitalGitHubMergeQueueView.qml": (
        "root.pullRequestRequested(",
        "root.refresh()",
    ),
    "HospitalRoomReportsView.qml": (
        "reportService.refresh()",
        "root.chatRequested()",
        "root.closeRequested()",
        "runtimeService.reportFeedback(",
    ),
    "HospitalRoundsView.qml": (
        "root.roundsService.refresh()",
        "root.activateSelectedRoom()",
    ),
    "HospitalSpecialistsView.qml": (
        "root.registryService.refreshPresence()",
    ),
}
for name, needles in commands.items():
    src = (ROOT / "widgets" / name).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in src, (name, needle)

# Where a new action has a fixed-height owner, the action must use the
# parent's actual height rather than force its 35px preferred height.
for name in views:
    text = (ROOT / "widgets" / name).read_text(encoding="utf-8")
    for found in re.finditer(r"(?m)^(\s*)HospitalActionButton \{\n", text):
        body = text[found.end():]
        closing = re.search(rf"(?m)^{re.escape(found.group(1))}\}}\s*$", body)
        assert closing, (name, "unterminated action")
        own_lines = body[:closing.start()].splitlines()
        top_indent = len(found.group(1)) + 4
        own_heights = [
            line.strip() for line in own_lines
            if line.strip().startswith("height:")
            and len(line) - len(line.lstrip(" ")) == top_indent
        ]
        assert len(own_heights) == 1, (name, found.start(), own_heights)
        assert own_heights[0] in (
            "height: Math.min(35, parent.height)",
            "height: parent.height",
            "height: 28",
        ), (name, own_heights)

print("Hospital ordinary ActionButton batch: PASS // 34 actions across 8 views")
