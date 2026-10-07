#!/usr/bin/env python3
"""Contracts for normal PULLS -> PR control integration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITW = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
WORK = (ROOT / "widgets/GitHubWorkItemsView.qml").read_text(encoding="utf-8")
CONTROL = (
    ROOT / "widgets/GitHubPullRequestControlView.qml"
).read_text(encoding="utf-8")
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


require(
    WORK,
    "signal pullRequestControlRequested(var row)",
    "PULLS list needs an internal detail-navigation signal",
)
require(
    WORK,
    "root.pullRequestControlRequested(",
    "PULLS OPEN must request the internal control surface",
)
require(WORK, 'label: "WEB"', "external GitHub navigation must remain available")
require(
    WORK,
    "Qt.openUrlExternally(sourceRow.itemUrl)",
    "WEB must retain external navigation",
)

for needle, label in (
    ("GitHubPullRequestLifecycleService {", "PR lifecycle host"),
    ("GitHubMergeQueueProvider {", "Merge Queue provider host"),
    ("GitHubMergeQueueLifecycleService {", "Merge Queue lifecycle host"),
    ("GitHubPullRequestReviewThreadProvider {", "thread provider host"),
    ("GitHubPullRequestReviewThreadLifecycleService {", "thread lifecycle host"),
):
    require(GITW, needle, label)

for needle, label in (
    ("property bool pullRequestControlOpen: false", "detail-open state"),
    ("property var selectedPullRequest: null", "selected PR snapshot"),
    ("function openPullRequestControl(row)", "detail open navigation"),
    ("function closePullRequestControl()", "detail close navigation"),
    ("function refreshSelectedPullRequest()", "selected-row rebinding"),
    ("function onPullsRefreshed()", "readback coordination"),
    ("GitHubPullRequestControlView {", "standalone PR control host"),
    ("onPullRequestControlRequested: function(row)", "list to detail wiring"),
    ("onTargetRefreshRequested:", "control to WorkItems refresh"),
):
    require(GITW, needle, label)

for needle, label in (
    ("githubWorkItemsService.rowNumber(", "PR number from WorkItems"),
    ("githubWorkItemsService.rowTitle(", "PR title from WorkItems"),
    ("githubWorkItemsService.rowState(", "PR state from WorkItems"),
    ("githubWorkItemsService.pullIsDraft(", "draft state from WorkItems"),
    ("(root.selectedPullRequest || {}).headRefOid", "head SHA from WorkItems"),
    ("(root.selectedPullRequest || {}).baseRefName", "base ref from WorkItems"),
    ("(root.selectedPullRequest || {}).headRefName", "head ref from WorkItems"),
):
    require(GITW, needle, label)

require(CONTROL, "signal closeRequested()", "PR control needs a close/back signal")
require(CONTROL, 'label: "← PULLS"', "PR control needs visible return navigation")
require(
    CONTROL,
    "onTriggered: root.closeRequested()",
    "return control must emit closeRequested",
)

for forbidden in (
    "GitInteractiveRebaseService",
    "GitInteractiveRebaseView",
    "GitChangeTransferService",
    "GitLineTransferService",
    "GitOperationRecoveryService",
):
    if forbidden in CONTROL or forbidden in WORK:
        errors.append(
            f"GitHub PR integration crossed local-Git exclusion zone: {forbidden}"
        )

if errors:
    print("POST-APOLLO PR INTEGRATION CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO PR INTEGRATION CONTRACTS // PASS")
print("checked PULLS list -> control navigation + readback coordination")
