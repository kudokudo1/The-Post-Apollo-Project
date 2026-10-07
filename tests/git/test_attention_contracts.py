#!/usr/bin/env python3
"""Focused static contracts for the cross-repository GitHub attention provider."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROVIDER_PATH = ROOT / "services/github/GitHubAttentionProvider.qml"
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


if not PROVIDER_PATH.exists():
    errors.append("missing services/github/GitHubAttentionProvider.qml")
    provider = ""
else:
    provider = PROVIDER_PATH.read_text(encoding="utf-8")


# Cross-repository input is normalized without depending on GitW or Hospital.
require(
    provider,
    "property var repositories: []",
    "attention provider must accept repository inputs",
)
require(
    provider,
    "function normalizeRepositories(values)",
    "repository inputs must be normalized",
)
require(
    provider,
    "function itemsForRepository(repository)",
    "provider must expose repository-scoped attention",
)
require(
    provider,
    "function itemsForState(stateName)",
    "provider must expose normalized attention-state filtering",
)
require(
    provider,
    "function repositoryState(repository)",
    "provider must expose per-repository read state",
)

# Viewer identity is required to distinguish generic review demand from work
# explicitly requested from the current operator.
require(
    provider,
    'viewer="$(gh api user --jq ".login"',
    "attention refresh must resolve the current GitHub viewer",
)
require(
    provider,
    "requestedFromMe",
    "provider must classify review requests aimed at the viewer",
)

# PR evidence comes from one read-only GraphQL pass plus exact-head fallbacks
# for checks when rollup evidence is absent.
for needle, label in (
    ("pullRequests(first:$limit,states:OPEN", "open pull requests must be queried"),
    ("reviewDecision", "review decision must be collected"),
    ("mergeStateStatus", "merge state must be collected"),
    ("mergeable", "mergeability must be collected"),
    ("reviewRequests(first:50)", "review requests must be collected"),
    ("statusCheckRollup", "check rollup must be collected"),
    ("commits/$sha/check-runs?per_page=100", "exact-SHA check runs need fallback"),
    ("commits/$sha/status", "exact-SHA status contexts need fallback"),
    ("commits/$sha/check-suites?per_page=100", "check suites need final fallback"),
):
    require(provider, needle, label)

# The normalized provider contract is deliberately broader than the visual
# NEEDS ME / FAILED / WAITING / READY buckets so Hospital can reason from facts.
for field in (
    "needsReview",
    "requestedFromMe",
    "failedChecks",
    "pendingChecks",
    "changesRequested",
    "waitingOnReviewer",
    "mergeable",
    "blocked",
    "waiting",
    "ready",
    "primaryState",
    "attentionStates",
):
    require(
        provider,
        field,
        f"normalized attention item must expose {field}",
    )

for state in (
    '"NEEDS_ME"',
    '"FAILED"',
    '"BLOCKED"',
    '"WAITING"',
    '"READY"',
    '"NEEDS_REVIEW"',
    '"CHANGES_REQUESTED"',
    '"WAITING_ON_REVIEWER"',
    '"PENDING_CHECKS"',
):
    require(
        provider,
        state,
        f"attention state {state} must remain available",
    )

# One broken repository must become repository evidence, not abort the entire
# multi-repository attention read.
require(
    provider,
    'state:"ERROR",error:$error,pullRequestCount:0',
    "per-repository failures must be represented as data",
)
require(
    provider,
    'state:"OK",error:"",pullRequestCount:$count',
    "successful repositories must preserve their own state",
)
require(
    provider,
    "failedRepositories",
    "partial refreshes must remain visible to callers",
)

# Doc 4 owns a read-only provider. It must not grow Git/GitHub mutation
# behavior or couple itself to Doc 3's recovery lane or the eventual UI host.
for forbidden in (
    "GitOperationJournalService",
    "GitOperationRecoveryService",
    "GitRepositorySnapshotService",
    "GitBranchWorkspaceService",
    "GitW",
    "HospitalW",
    "gh pr merge",
    "gh pr edit",
    "gh pr close",
    "gh pr review",
    "gh issue edit",
    "gh issue close",
    "git -C",
    'gh api -X ',
    'gh api --method ',
):
    if forbidden in provider:
        errors.append(
            f"read-only attention boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO GITHUB ATTENTION CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GITHUB ATTENTION CONTRACTS // PASS")
print("checked standalone cross-repository attention provider")
