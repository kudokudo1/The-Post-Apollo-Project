#!/usr/bin/env python3
"""Focused static contracts for the read-only GitHub merge queue provider."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVIDER_PATH = ROOT / "services/github/GitHubMergeQueueProvider.qml"
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


if not PROVIDER_PATH.exists():
    errors.append("missing services/github/GitHubMergeQueueProvider.qml")
    provider = ""
else:
    provider = PROVIDER_PATH.read_text(encoding="utf-8")


# The provider reads GitHub's native queue object rather than inferring queue
# state from ordinary PR mergeability alone.
require(
    provider,
    "mergeQueue(branch:$branch)",
    "explicit-branch queue reads must use Repository.mergeQueue",
)
require(
    provider,
    "mergeQueue{",
    "default-branch queue reads must use Repository.mergeQueue",
)
require(
    provider,
    "entries(first:$limit)",
    "queue entries must be read directly",
)
require(
    provider,
    "nextEntryEstimatedTimeToMerge",
    "queue-level estimated wait must remain available",
)
require(
    provider,
    "configuration{checkResponseTimeout",
    "queue configuration must be observable",
)

# Queue entry state is first-class and retains enough PR identity to hand off
# to GitW/Hospital later without this provider owning either UI.
for field in (
    "position",
    "state",
    "enqueuedAt",
    "estimatedTimeToMerge",
    "jump",
    "solo",
    "enqueuer",
    "baseCommit",
    "headCommit",
    "pullRequest",
    "mergeStateStatus",
    "mergeable",
    "reviewDecision",
):
    require(
        provider,
        field,
        f"merge queue entry must retain {field}",
    )

for state in (
    '"AWAITING_CHECKS"',
    '"LOCKED"',
    '"MERGEABLE"',
    '"QUEUED"',
    '"UNMERGEABLE"',
):
    require(
        provider,
        state,
        f"native merge queue state {state} must remain classified",
    )

require(
    provider,
    "function entryForPullRequest(number)",
    "callers must be able to resolve a PR's queue entry",
)
require(
    provider,
    "function countState(stateName)",
    "callers must be able to summarize native queue states",
)
require(
    provider,
    "MERGE QUEUE // NOT CONFIGURED",
    "absence of a queue must differ from provider failure",
)

# This slice is observation only. Enqueue/dequeue mechanics are deliberately
# deferred until the mutation architecture is ready for that ownership.
for forbidden in (
    "GitOperationJournalService",
    "GitOperationRecoveryService",
    "GitRepositorySnapshotService",
    "GitBranchWorkspaceService",
    "GitW",
    "HospitalW",
    "enqueuePullRequest",
    "dequeuePullRequest",
    "gh pr merge",
    "gh pr edit",
    "gh api -X ",
    "gh api --method ",
    "git -C",
):
    if forbidden in provider:
        errors.append(
            f"read-only merge queue boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO GITHUB MERGE QUEUE CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GITHUB MERGE QUEUE CONTRACTS // PASS")
print("checked standalone read-only merge queue provider")
