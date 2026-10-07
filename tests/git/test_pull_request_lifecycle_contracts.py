#!/usr/bin/env python3
"""Focused contracts for the standalone GitHub pull-request lifecycle service."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_PATH = (
    ROOT
    / "services/github/GitHubPullRequestLifecycleService.qml"
)
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


if not SERVICE_PATH.exists():
    errors.append(
        "missing services/github/GitHubPullRequestLifecycleService.qml"
    )
    service = ""
else:
    service = SERVICE_PATH.read_text(encoding="utf-8")


# Ordinary PR lifecycle must exist as a standalone backend rather than being
# embedded into GitW, WorkItems, Projects, or the local-Git mutation stack.
for function_name in (
    "createPullRequest",
    "editPullRequest",
    "updateLabels",
    "updateAssignees",
    "updateReviewers",
    "setMilestone",
    "clearMilestone",
    "commentPullRequest",
    "markReady",
    "convertToDraft",
    "reviewPullRequest",
    "closePullRequest",
    "reopenPullRequest",
    "updateBranch",
    "mergePullRequest",
):
    require(
        service,
        f"function {function_name}(",
        f"PR lifecycle must expose {function_name}",
    )

# Native GitHub CLI PR mechanics.
for needle, label in (
    ('"pr",\n            "create"', "PR create"),
    ('"pr",\n            "edit"', "PR edit"),
    ('"--head"', "PR head selection"),
    ('"--base"', "PR base selection"),
    ('"--draft"', "draft PR creation"),
    ('"--add-label"', "label add"),
    ('"--remove-label"', "label remove"),
    ('"--add-assignee"', "assignee add"),
    ('"--remove-assignee"', "assignee remove"),
    ('"--add-reviewer"', "reviewer add"),
    ('"--remove-reviewer"', "reviewer remove"),
    ('"--milestone"', "milestone set"),
    ('"--remove-milestone"', "milestone clear"),
    ('"pr",\n                "comment"', "PR comment"),
    ('"pr",\n                "ready"', "ready/draft transition"),
    ('"--undo"', "ready-to-draft transition"),
    ('"pr",\n            "review"', "review submission"),
    ('"--approve"', "approve review"),
    ('"--comment"', "comment review"),
    ('"--request-changes"', "request-changes review"),
    ('"pr",\n            "close"', "PR close"),
    ('"pr",\n            "reopen"', "PR reopen"),
    ('"pr",\n            "update-branch"', "PR branch update"),
    ('"pr",\n            "merge"', "PR merge"),
):
    require(service, needle, label)

# Riskier mutations must be deliberately armed.
require(
    service,
    "PR CLOSE REFUSED // EXPLICIT CONFIRMATION REQUIRED",
    "closing must require explicit confirmation",
)
require(
    service,
    "PR UPDATE BRANCH REFUSED // EXPLICIT CONFIRMATION REQUIRED",
    "updating a PR branch must require explicit confirmation",
)
require(
    service,
    "PR MERGE REFUSED // EXPLICIT CONFIRMATION REQUIRED",
    "merge must require explicit confirmation",
)

# Merge must be pinned to the reviewed head SHA rather than merging whatever
# happens to be current when the command runs.
require(
    service,
    'if (!/^[0-9a-fA-F]{40}$/.test(cleanHead))',
    "merge must require a full expected head SHA",
)
require(
    service,
    '"--match-head-commit"',
    "merge must pass GitHub CLI head-SHA protection",
)
for method in ('"merge"', '"squash"', '"rebase"'):
    require(
        service,
        method,
        f"merge mode {method} must remain supported",
    )

# Update-branch must make rebase-vs-merge behavior explicit.
require(
    service,
    'Boolean(rebase) ? "update-branch-rebase" : "update-branch"',
    "update-branch operation must identify rebase mode",
)
require(
    service,
    'args.push("--rebase")',
    "rebase branch-update mode must be explicit",
)

# Reviews are constrained to the three normal submitted-review modes.
require(
    service,
    '["approve", "comment", "request-changes"]',
    "review mode must be validated",
)
require(
    service,
    'cleanMode !== "approve" && !cleanBody',
    "comment/change-request reviews must require a body",
)

# Creation returns a URL; do not infer the PR number locally.
require(
    service,
    "function createdPullRequestTarget(text)",
    "PR creation must recover the returned PR URL",
)
require(
    service,
    r"/^https:\/\/github\.com\/[^/]+\/[^/]+\/pull\/\d+$/",
    "created PR URL must be validated",
)

# A successful mutation is not complete until the affected PR is read back.
require(
    service,
    "function startEvidenceRead(target)",
    "successful mutations must begin evidence verification",
)
require(
    service,
    '"pr",\n            "view"',
    "verification must use gh pr view",
)
for field in (
    "number,title,body,state,url,isDraft",
    "labels,assignees,milestone,author",
    "baseRefName,baseRefOid,headRefName,headRefOid",
    "mergeable,mergeStateStatus,reviewDecision,reviewRequests",
    "latestReviews,statusCheckRollup,autoMergeRequest",
):
    require(
        service,
        field,
        f"PR evidence read must retain {field}",
    )

require(
    service,
    "property bool mutationSucceeded: false",
    "mutation success must be distinct from evidence success",
)
require(
    service,
    "property bool evidenceVerified: false",
    "evidence verification must be first-class",
)
require(
    service,
    "MUTATED // EVIDENCE UNVERIFIED",
    "post-mutation read failure must remain truthful",
)
require(
    service,
    "signal pullRequestChanged(string repository, int number, string url)",
    "service needs a neutral refresh/integration seam",
)
require(
    service,
    "signal mutationFinished(",
    "service must expose completion evidence",
)

# Ownership boundaries: this service owns ordinary GitHub PR lifecycle only.
# Project membership, merge-queue state, local Git mutation/recovery, and UI
# integration remain in their existing services/owners.
for forbidden in (
    "GitHubProjectsService",
    "GitHubMergeQueueProvider",
    "gh project",
    "enqueuePullRequest",
    "dequeuePullRequest",
    "GitOperationJournalService",
    "GitOperationRecoveryService",
    "GitRepositorySnapshotService",
    "GitBranchWorkspaceService",
    "GitChangeTransferService",
    "GitW",
    "GitHubWorkItemsService",
    "GitHubWorkItemsView",
    "HospitalW",
    "git -C",
):
    if forbidden in service:
        errors.append(
            f"PR lifecycle ownership boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO GITHUB PR LIFECYCLE CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GITHUB PR LIFECYCLE CONTRACTS // PASS")
print("checked standalone ordinary pull-request lifecycle service")
