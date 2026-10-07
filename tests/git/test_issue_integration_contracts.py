#!/usr/bin/env python3
"""Contracts for normal ISSUES -> Issue lifecycle integration."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITW = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
WORK = (ROOT / "widgets/GitHubWorkItemsView.qml").read_text(encoding="utf-8")
VIEW = (ROOT / "widgets/GitHubIssueControlView.qml").read_text(encoding="utf-8")
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


for needle, label in (
    ("signal issueControlRequested(var row)", "issue detail signal"),
    ("signal issueCreateRequested()", "issue create signal"),
    ('label: "NEW ISSUE"', "visible create entry point"),
    ("root.issueControlRequested(", "issue OPEN internal navigation"),
    ('label: "WEB"', "explicit external navigation"),
):
    require(WORK, needle, label)

for needle, label in (
    ("GitHubIssueLifecycleService {", "Issue lifecycle host"),
    ("property bool issueControlOpen: false", "Issue detail-open state"),
    ("property bool issueCreateMode: false", "Issue create mode"),
    ("property var selectedIssue: null", "selected Issue snapshot"),
    ("function openIssueControl(row)", "Issue detail navigation"),
    ("function openIssueCreate()", "Issue create navigation"),
    ("function closeIssueControl()", "Issue close navigation"),
    ("function refreshSelectedIssue()", "Issue row rebinding"),
    ("function onIssuesRefreshed()", "Issue readback coordination"),
    ("GitHubIssueControlView {", "Issue control host"),
    ("onIssueControlRequested: function(row)", "list to Issue detail wiring"),
    ("onIssueCreateRequested:", "list to Issue create wiring"),
    ("onTargetRefreshRequested:", "Issue control to WorkItems refresh"),
):
    require(GITW, needle, label)

for needle, label in (
    ("createIssue(", "Issue creation"),
    ("editIssue(", "Issue edits"),
    ("updateLabels(", "Issue labels"),
    ("updateAssignees(", "Issue assignees"),
    ("setMilestone(", "Issue milestone set"),
    ("clearMilestone(", "Issue milestone clear"),
    ("commentIssue(", "Issue comments"),
    ("closeIssue(", "Issue close"),
    ("reopenIssue(", "Issue reopen"),
    ("EXPLICIT", "view/backend confirmation semantics"),
    ('label: "← ISSUES"', "visible Issue return path"),
):
    if needle == "EXPLICIT":
        require(
            (ROOT / "services/github/GitHubIssueLifecycleService.qml")
            .read_text(encoding="utf-8"),
            "ISSUE CLOSE REFUSED // EXPLICIT CONFIRMATION REQUIRED",
            label,
        )
    else:
        require(VIEW, needle, label)

for forbidden in (
    "GitInteractiveRebaseService",
    "GitChangeTransferService",
    "GitLineTransferService",
    "GitOperationRecoveryService",
):
    if forbidden in VIEW or forbidden in WORK:
        errors.append(
            f"GitHub Issue integration crossed local-Git exclusion zone: {forbidden}"
        )

if errors:
    print("POST-APOLLO ISSUE INTEGRATION CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO ISSUE INTEGRATION CONTRACTS // PASS")
print("checked ISSUES create/detail lifecycle integration")
