#!/usr/bin/env python3
"""Focused contracts for the standalone GitHub Issue lifecycle service."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_PATH = ROOT / "services/github/GitHubIssueLifecycleService.qml"
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


if not SERVICE_PATH.exists():
    errors.append("missing services/github/GitHubIssueLifecycleService.qml")
    service = ""
else:
    service = SERVICE_PATH.read_text(encoding="utf-8")


# Ordinary Issue lifecycle must exist independently of GitHub Projects.
for function_name in (
    "createIssue",
    "editIssue",
    "updateLabels",
    "updateAssignees",
    "setMilestone",
    "clearMilestone",
    "commentIssue",
    "closeIssue",
    "reopenIssue",
):
    require(
        service,
        f"function {function_name}(",
        f"Issue lifecycle must expose {function_name}",
    )

# Use the native GitHub CLI Issue commands and their explicit mutation flags.
for needle, label in (
    ('"issue",\n            "create"', "Issue create command"),
    ('"issue",\n            "edit"', "Issue edit command"),
    ('"--add-label"', "label add"),
    ('"--remove-label"', "label remove"),
    ('"--add-assignee"', "assignee add"),
    ('"--remove-assignee"', "assignee remove"),
    ('"--milestone"', "milestone set"),
    ('"--remove-milestone"', "milestone clear"),
    ('"issue",\n                "comment"', "Issue comment command"),
    ('"issue",\n            "close"', "Issue close command"),
    ('"issue",\n            "reopen"', "Issue reopen command"),
):
    require(service, needle, label)

# Closing an Issue is destructive enough to require an explicit confirmation,
# and the service only accepts GitHub's ordinary completed/not-planned reasons.
require(
    service,
    "if (!confirmed)",
    "Issue close must require explicit confirmation",
)
require(
    service,
    "EXPLICIT CONFIRMATION REQUIRED",
    "close refusal must explain its confirmation requirement",
)
require(
    service,
    '["completed", "not planned"]',
    "close reason must be validated",
)

# A zero exit code is not the end of the operation. Read the resulting Issue
# back so callers have evidence of the actual GitHub state.
require(
    service,
    "function startEvidenceRead(target)",
    "successful mutations must begin evidence verification",
)
require(
    service,
    '"issue",\n            "view"',
    "evidence verification must use gh issue view",
)
for field in (
    "number,title,body,state,stateReason,url",
    "labels,assignees,milestone,author",
    "createdAt,updatedAt,closed,closedAt",
):
    require(
        service,
        field,
        f"evidence read must retain {field}",
    )

require(
    service,
    "property bool mutationSucceeded: false",
    "mutation outcome must be distinct from evidence outcome",
)
require(
    service,
    "property bool evidenceVerified: false",
    "evidence verification must be first-class",
)
require(
    service,
    "MUTATED // EVIDENCE UNVERIFIED",
    "uncertain post-mutation evidence must remain truthful",
)
require(
    service,
    "signal issueChanged(string repository, int number, string url)",
    "service must expose a neutral refresh/integration seam",
)
require(
    service,
    "signal mutationFinished(",
    "service must expose operation completion evidence",
)

# Create is allowed to return an Issue URL instead of a number. The service
# must derive the target from GitHub output, not infer a number locally.
require(
    service,
    "function createdIssueTarget(text)",
    "create must recover the returned Issue URL",
)
require(
    service,
    r"/^https:\/\/github\.com\/",
    "created Issue URL must be validated",
)

# This service owns Issue objects only. Project membership/status remains in
# GitHubProjectsService; local Git history/recovery remains Doc 3's lane.
for forbidden in (
    "GitHubProjectsService",
    "gh project",
    "--add-project",
    "--remove-project",
    "GitOperationJournalService",
    "GitOperationRecoveryService",
    "GitRepositorySnapshotService",
    "GitBranchWorkspaceService",
    "GitW",
    "HospitalW",
    "git -C",
    "gh pr ",
):
    if forbidden in service:
        errors.append(
            f"Issue lifecycle ownership boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO GITHUB ISSUE LIFECYCLE CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GITHUB ISSUE LIFECYCLE CONTRACTS // PASS")
print("checked standalone ordinary Issue lifecycle service")
