#!/usr/bin/env python3
"""Static contracts for the reusable inset-aware section frame."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/SectionFrame.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "components/qmldir").read_text(encoding="utf-8")
WORKFLOW_LIBRARY = (ROOT / "widgets/WorkflowLibraryView.qml").read_text(encoding="utf-8")
REPOSITORY_PROFILE = (ROOT / "widgets/RepositoryProfileView.qml").read_text(encoding="utf-8")
HOSPITAL_CHARTS = (ROOT / "widgets/HospitalChartsView.qml").read_text(encoding="utf-8")
GIT_REPOSITORY = (ROOT / "widgets/GitRepositoryView.qml").read_text(encoding="utf-8")
GIT_CHANGES = (ROOT / "widgets/GitChangesView.qml").read_text(encoding="utf-8")
GIT_TRANSFER = (ROOT / "widgets/GitChangeTransferView.qml").read_text(encoding="utf-8")
GIT_CONFLICT_EDITOR = (ROOT / "widgets/GitConflictEditorView.qml").read_text(encoding="utf-8")
GIT_OPERATIONS = (ROOT / "widgets/GitOperationsView.qml").read_text(encoding="utf-8")
GITHUB_ISSUE = (ROOT / "widgets/GitHubIssueControlView.qml").read_text(encoding="utf-8")
GITHUB_PROJECTS = (ROOT / "widgets/GitHubProjectsView.qml").read_text(encoding="utf-8")
GITHUB_PR = (ROOT / "widgets/GitHubPullRequestControlView.qml").read_text(encoding="utf-8")
GIT_ABSORB = (ROOT / "widgets/GitHistoryAbsorbView.qml").read_text(encoding="utf-8")
GIT_SPLIT_HUNK = (ROOT / "widgets/GitHistorySplitHunkView.qml").read_text(encoding="utf-8")
GIT_SPLIT_LINE = (ROOT / "widgets/GitHistorySplitLineView.qml").read_text(encoding="utf-8")
GIT_SPLIT_FILE = (ROOT / "widgets/GitHistorySplitView.qml").read_text(encoding="utf-8")
GIT_SURGERY = (ROOT / "widgets/GitHistorySurgeryView.qml").read_text(encoding="utf-8")
GIT_REBASE_SESSION = (ROOT / "widgets/GitInteractiveRebaseSessionView.qml").read_text(encoding="utf-8")
GIT_LINE_TRANSFER = (ROOT / "widgets/GitLineTransferView.qml").read_text(encoding="utf-8")
GIT_BRANCHES = (ROOT / "widgets/GitBranchesView.qml").read_text(encoding="utf-8")
GIT_HISTORY = (ROOT / "widgets/GitHistoryView.qml").read_text(encoding="utf-8")
GITHUB_WORK_ITEMS = (ROOT / "widgets/GitHubWorkItemsView.qml").read_text(encoding="utf-8")
GIT_REBASE = (ROOT / "widgets/GitInteractiveRebaseView.qml").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


for needle, message in (
    ("default property alias contentData: contentHost.data", "arbitrary section content slot"),
    ("SurfaceFrame {", "section must compose the neutral surface primitive"),
    ("property alias fillColor: surface.fillColor", "fill forwarding"),
    ("property alias fillOpacity: surface.fillOpacity", "fill-opacity forwarding"),
    ("property alias fillVisible: surface.fillVisible", "fill visibility forwarding"),
    ("property alias borderColor: surface.borderColor", "border forwarding"),
    ("property alias borderOpacity: surface.borderOpacity", "border-opacity forwarding"),
    ("property alias borderWidth: surface.borderWidth", "border-width forwarding"),
    ("property alias borderVisible: surface.borderVisible", "border visibility forwarding"),
    ("property alias radius: surface.radius", "radius forwarding"),
    ("property alias clipContent: surface.clipContent", "clip forwarding"),
    ("property real inset: 0", "lossless zero-inset default"),
    ("property real leftInset: inset", "left inset override contract"),
    ("property real rightInset: inset", "right inset override contract"),
    ("property real topInset: inset", "top inset override contract"),
    ("property real bottomInset: inset", "bottom inset override contract"),
    ("leftMargin: sectionFrame.leftInset", "left inset geometry"),
    ("rightMargin: sectionFrame.rightInset", "right inset geometry"),
    ("topMargin: sectionFrame.topInset", "top inset geometry"),
    ("bottomMargin: sectionFrame.bottomInset", "bottom inset geometry"),
    ("readonly property Item frameSource: surface.frameSource", "external frame effect source"),
    ("readonly property Item fillSource: surface.fillSource", "external fill effect source"),
    ("readonly property Item contentItem: contentHost", "content host exposure"),
):
    require(COMPONENT, needle, message)

require(QMLDIR, "SectionFrame 1.0 SectionFrame.qml", "component registration")

for forbidden in (
    "MouseArea {",
    "TapHandler {",
    "DropShadow {",
    "SafeDropShadow {",
    "RectangularShadow {",
    "Row {",
    "Column {",
    "RowLayout {",
    "ColumnLayout {",
):
    assert forbidden not in COMPONENT, (
        "SectionFrame must own inset geometry only, not interaction/layout/effects: "
        + forbidden
    )

assert COMPONENT.count("SurfaceFrame {") == 1, (
    "SectionFrame must have exactly one shared surface implementation"
)
assert "property real inset: 7" not in COMPONENT
assert "property real inset: 8" not in COMPONENT

# First lossless proof consumers: preserve the two established flat workbench panes.
for needle, message in (
    ("SectionFrame {\n                id: queuePane", "queue pane must use SectionFrame"),
    ("fillColor: Colors.dark\n                borderWidth: 1\n                borderColor: Colors.orange\n                inset: 8", "queue pane visual/inset values"),
    ("SectionFrame {\n            id: workflowPane", "workflow pane must use SectionFrame"),
    ("fillColor: Colors.dark\n            borderWidth: 1\n            borderColor: Colors.cyan\n            inset: 9", "workflow pane visual/inset values"),
):
    require(WORKFLOW_LIBRARY, needle, message)

assert "Rectangle {\n                id: queuePane" not in WORKFLOW_LIBRARY
assert "Rectangle {\n            id: workflowPane" not in WORKFLOW_LIBRARY

# Additional flat-workbench proof consumers preserve their original shell values.
for needle, message in (
    ("SectionFrame {\n                        id: procedureReport", "procedure report must use SectionFrame"),
    ("fillColor: Colors.black\n                        borderWidth: 1\n                        borderColor:\n                            root.githubService.batchStepFailureCount > 0\n                            ? Colors.red\n                            : Colors.cyan\n                        inset: 5", "procedure report dynamic border and inset"),
    ("fillColor: Colors.dark\n                borderWidth: 1\n                borderColor: Colors.blue\n                inset: 8", "saved sets pane visual/inset values"),
):
    require(WORKFLOW_LIBRARY, needle, message)

assert "Rectangle {\n                        id: procedureReport" not in WORKFLOW_LIBRARY

# Repository Profile proves SectionFrame around shells that contain controls without owning them.
for needle, message in (
    ("SectionFrame {\n                    width: parent.width\n                    height: 292\n                    fillColor: Colors.dark\n                    borderWidth: 1\n                    borderColor: Colors.blue\n                    inset: 8", "profile patch shell values"),
    ("SectionFrame {\n                    width: parent.width\n                    height: parent.height - 300\n                    fillColor: Colors.dark\n                    borderWidth: 1\n                    borderColor:", "review/apply shell must use SectionFrame"),
    ("root.profileService.reviewReady\n                        ? Colors.orange\n                        : Colors.cyan\n                    inset: 8", "review/apply dynamic border and inset"),
    ("SectionFrame {\n            width: parent.width\n            height: 42\n            fillColor: Colors.dark\n            borderWidth: 1\n            borderColor: Colors.blue\n            inset: 8", "account profile header shell values"),
):
    require(REPOSITORY_PROFILE, needle, message)

# Hospital Charts proves the same flat workbench shell grammar across domains.
for needle, message in (
    ("SectionFrame {\n            width: parent.width\n            height: 42\n            fillColor: Colors.dark\n            borderWidth: 1\n            borderColor: Colors.green\n            inset: 7", "hospital chart header shell"),
    ("root.selectedEntry\n                    ? root.statusColor(root.selectedEntry.status)\n                    : Colors.green\n                inset: 10", "selected chart detail dynamic border and inset"),
    ("SectionFrame {\n                width: parent.width\n                height: 42\n                fillColor: Colors.black\n                borderWidth: 1\n                borderColor: Colors.magenta\n                inset: 7", "suggestions header shell"),
    ("root.selectedSuggestion\n                        ? Colors.magenta : Colors.blue\n                    inset: 10", "selected suggestion detail dynamic border and inset"),
):
    require(HOSPITAL_CHARTS, needle, message)

# Git Repository proves nested and dynamic workbench shell composition.
for needle, message in (
    ("SectionFrame {\n            width: parent.width\n            height: 62\n            fillColor: Colors.dark\n            borderWidth: 1\n            borderColor: Colors.orange\n            inset: 8", "repository mechanics header"),
    ("height: 82\n                            fillColor: Colors.dark\n                            borderWidth: 1\n                            borderColor: Colors.magenta\n                            inset: 7", "remote intelligence panel"),
    ("SectionFrame {\n                    width: parent.width - 478\n                    height: parent.height\n                    fillColor: Colors.black\n                    borderWidth: 1\n                    borderColor: Colors.magenta\n                    inset: 8", "tag operations outer shell"),
    ("root.selectedTagRow()\n                                  )\n                                : Colors.orange\n                            inset: 7", "tag intelligence dynamic border and inset"),
    ("root.tagRemoteStateColor()\n                            inset: 7", "tag remote status dynamic border and inset"),
    ("SectionFrame {\n                    width: 560\n                    height: parent.height\n                    fillColor: Colors.dark\n                    borderWidth: 1\n                    borderColor: Colors.green\n                    inset: 7", "local config pane"),
):
    require(GIT_REPOSITORY, needle, message)

# Broad flat-workbench rollout: representative values in every migrated view.
for text_value, needle, message in (
    (GIT_CHANGES, "height: 62\n            fillColor: Colors.dark\n            borderWidth: 1\n            borderColor: Colors.cyan\n            inset: 8", "Git Changes header"),
    (GIT_CHANGES, "width: parent.width - 438\n                    height: parent.height\n                    fillColor: Colors.black\n                    borderWidth: 1\n                    borderColor: Colors.magenta\n                    inset: 7", "Git Changes diff shell"),
    (GIT_TRANSFER, "height: 46\n            fillColor: Colors.black\n            borderWidth: 1\n            borderColor: Colors.orange\n            inset: 7", "transfer scope notice"),
    (GIT_TRANSFER, "root.previewMatchesSelection\n                            ? Colors.green\n                            : Colors.cyan\n                        inset: 7", "transfer preview shell"),
    (GIT_CONFLICT_EDITOR, "conflictService.unresolvedCount > 0\n                ? Colors.orange\n                : Colors.green\n            inset: 6", "conflict editor status shell"),
    (GIT_OPERATIONS, "width: parent.width - operationList.parent.width - 8\n                height: parent.height\n                fillColor: Colors.dark\n                borderWidth: 1\n                borderColor: Colors.magenta\n                inset: 9", "operations detail shell"),
    (GIT_OPERATIONS, "root.statusText.indexOf(\"REFUSED\") >= 0\n                ? Colors.red\n                : Colors.cyan\n            inset: 8", "operations footer shell"),
    (GITHUB_ISSUE, "height: 52\n            fillColor: Colors.black\n            borderWidth: 1\n            borderColor: Colors.magenta\n            inset: 7", "issue header shell"),
    (GITHUB_ISSUE, "visible: !root.createMode\n                    width: parent.width\n                    height: 80\n                    fillColor: Colors.black\n                    borderWidth: 1\n                    borderColor: Colors.red\n                    inset: 8", "issue close shell"),
    (GITHUB_PROJECTS, "fillColor: Colors.dark\n                borderWidth: 1\n                borderColor: Colors.cyan\n                inset: 10", "projects primary shell"),
    (GITHUB_PR, "height: 52\n            fillColor: Colors.black\n            borderWidth: 1\n            borderColor: Colors.magenta\n            inset: 7", "pull request header shell"),
    (GITHUB_PR, "height: 78\n                    fillColor: Colors.black\n                    borderWidth: 1\n                    borderColor: Colors.red\n                    inset: 8", "pull request merge shell"),
    (GITHUB_PR, "? Colors.orange\n                    : Colors.blue\n                inset: 8", "pull request preview shell"),
):
    require(text_value, needle, message)

# History/rebase/transfer rollout keeps strict-operation shells lossless.
for text_value, needle, message in (
    (GIT_ABSORB, "width: parent.width - Math.floor(parent.width * 0.56) - 8\n                height: parent.height\n                fillColor: Colors.black\n                borderWidth: 1\n                borderColor: Colors.orange\n                inset: 8", "absorb strict slice shell"),
    (GIT_ABSORB, "height: 70\n                        fillColor: Colors.dark\n                        borderWidth: 1\n                        borderColor: Colors.cyan\n                        inset: 7", "absorb undo contract shell"),
    (GIT_SPLIT_HUNK, "height: 92\n                        fillColor: Colors.dark\n                        borderWidth: 1\n                        borderColor: Colors.orange\n                        inset: 7", "hunk split strict shell"),
    (GIT_SPLIT_LINE, "height: 104\n                        fillColor: Colors.dark\n                        borderWidth: 1\n                        borderColor: Colors.magenta\n                        inset: 7", "line split strict shell"),
    (GIT_SPLIT_FILE, "height: 86\n                        fillColor: Colors.dark\n                        borderWidth: 1\n                        borderColor: Colors.orange\n                        inset: 7", "file split strict shell"),
    (GIT_SURGERY, "height: 76\n                        fillColor: Colors.dark\n                        borderWidth: 1\n                        borderColor: Colors.orange\n                        inset: 7", "history surgery strict shell"),
    (GIT_REBASE_SESSION, "height: 84\n            fillColor: Colors.black\n            borderWidth: 1\n            borderColor: Colors.cyan\n            inset: 7", "rebase session state shell"),
    (GIT_REBASE_SESSION, "sessionService.lastError\n                ? Colors.red\n                : Colors.cyan\n            inset: 7", "rebase session footer"),
    (GIT_LINE_TRANSFER, "width: parent.width - 438\n                height: parent.height\n                fillColor: Colors.black\n                borderWidth: 1\n                borderColor: Colors.magenta\n                inset: 8", "line transfer control shell"),
    (GIT_LINE_TRANSFER, "root.previewMatchesSelection\n                            ? Colors.green\n                            : Colors.cyan\n                        inset: 7", "line transfer preview shell"),
):
    require(text_value, needle, message)

# Final Git/GitHub flat-workbench rollout.
for text_value, needle, message in (
    (GIT_BRANCHES, "id: inspector\n\n                width: parent.width - mapPane.width - parent.spacing\n                height: parent.height\n                fillColor: Colors.dark\n                borderWidth: 1", "branch inspector shell"),
    (GIT_BRANCHES, "root.newBranchBlockReason()\n                                    ? Colors.orange\n                                    : Colors.green\n                                inset: 7", "new branch preview shell"),
    (GIT_BRANCHES, "root.managementMessage.indexOf(\"ARMED\") === 0\n                                ? Colors.orange\n                                : Colors.cyan\n                            inset: 7", "branch management status shell"),
    (GIT_HISTORY, "width: parent.width - 528\n                    height: parent.height\n                    fillColor: Colors.black\n                    borderWidth: 1\n                    borderColor: Colors.orange\n                    inset: 7", "history inspector shell"),
    (GIT_HISTORY, "root.queryHasFilters()\n                                ? Colors.green\n                                : Colors.cyan\n                            inset: 6", "history query summary shell"),
    (GIT_HISTORY, "width: parent.width - 478\n                    height: parent.height\n                    fillColor: Colors.black\n                    borderWidth: 1\n                    borderColor: Colors.cyan\n                    inset: 8", "history recovery shell"),
    (GIT_HISTORY, "width: 360\n                    height: parent.height\n                    fillColor: Colors.dark\n                    borderWidth: 1\n                    borderColor: Colors.orange\n                    inset: 8", "history compare shell"),
    (GITHUB_WORK_ITEMS, "height: 54\n            fillColor: Colors.dark\n            borderWidth: 1\n            borderColor: Colors.cyan\n            inset: 8", "work items header shell"),
    (GIT_REBASE, "rebaseService.lastError\n                ? Colors.red\n                : rebaseService.armed\n                ? Colors.orange\n                : Colors.cyan\n            inset: 7", "interactive rebase status shell"),
    (GIT_REBASE, "width: parent.width - Math.floor(parent.width * 0.57) - 8\n                height: parent.height\n                fillColor: Colors.black\n                borderWidth: 1\n                borderColor: Colors.magenta\n                inset: 8", "interactive rebase control shell"),
):
    require(text_value, needle, message)

print("Section frame contracts: PASS")
