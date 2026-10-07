#!/usr/bin/env python3
"""Focused contracts for GitHub PR review-thread lifecycle actions."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (
    ROOT
    / "services/github/GitHubPullRequestReviewThreadLifecycleService.qml"
)
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


if not SERVICE.exists():
    errors.append("missing GitHubPullRequestReviewThreadLifecycleService.qml")
    service = ""
else:
    service = SERVICE.read_text(encoding="utf-8")


for function_name in (
    "replyToThread",
    "resolveThread",
    "unresolveThread",
    "threadFromResponse",
    "preflightAllowed",
    "startMutation",
    "startVerification",
    "verifyResult",
):
    require(
        service,
        f"function {function_name}(",
        f"review-thread lifecycle must expose {function_name}",
    )

# Every mutation starts from a fresh native reviewThreads read so stale UI
# thread state is not trusted.
require(
    service,
    "reviewThreads(first:100)",
    "actions must preflight against current native review threads",
)
require(
    service,
    "REVIEW THREAD NOT FOUND IN FRESH PR READ",
    "stale/missing thread IDs must be refused",
)
for needle, label in (
    ("viewerCanReply", "fresh reply permission"),
    ("viewerCanResolve", "fresh resolve permission"),
    ("viewerCanUnresolve", "fresh unresolve permission"),
    ("isResolved", "fresh resolved state"),
):
    require(service, needle, label)

# Replies use GitHub's required top-level review comment database identity.
require(
    service,
    "fullDatabaseId",
    "thread read must retain fullDatabaseId",
)
require(
    service,
    "TOP-LEVEL COMMENT ID DOES NOT MATCH FRESH THREAD",
    "reply must pin to the thread's top-level comment",
)
require(
    service,
    '"/comments/"',
    "reply must address a concrete review comment",
)
require(
    service,
    '"/replies"',
    "reply must use the review-comment reply endpoint",
)
require(
    service,
    '"--method", "POST"',
    "reply must use POST",
)

# Resolve/unresolve are explicit GraphQL review-thread mutations.
require(
    service,
    "resolveReviewThread(input:{threadId:$threadId})",
    "resolve mutation",
)
require(
    service,
    "unresolveReviewThread(input:{threadId:$threadId})",
    "unresolve mutation",
)
require(
    service,
    "THREAD RESOLVE REFUSED // EXPLICIT CONFIRMATION REQUIRED",
    "resolve must require explicit confirmation",
)
require(
    service,
    "THREAD UNRESOLVE REFUSED // EXPLICIT CONFIRMATION REQUIRED",
    "unresolve must require explicit confirmation",
)

# The mutation result is not trusted until the affected native thread is read
# back. Replies verify the returned REST node_id against GraphQL comment.id;
# state changes verify isResolved.
for needle, label in (
    ("REPLY MUTATION DID NOT RETURN COMMENT NODE ID", "reply node identity"),
    ("REPLY NOT VISIBLE AFTER MUTATION", "reply readback"),
    ("THREAD COMMENT COUNT DID NOT ADVANCE", "reply count readback"),
    ("RESOLVE NOT VISIBLE AFTER MUTATION", "resolve readback"),
    ("UNRESOLVE NOT VISIBLE AFTER MUTATION", "unresolve readback"),
    ("MUTATED // EVIDENCE UNVERIFIED", "truthful verification failure"),
):
    require(service, needle, label)

require(
    service,
    "response.node_id",
    "reply verification must use stable REST node_id",
)
require(
    service,
    "createdReplyNodeId",
    "reply node identity must be first-class",
)
require(
    service,
    "signal threadChanged(",
    "service must expose a neutral provider-refresh handoff",
)
require(
    service,
    "signal mutationFinished(",
    "service must expose mutation/evidence completion",
)
require(
    service,
    "const timedOutPhase = root.phase;",
    "timeout handling must preserve operation phase",
)

# Standalone GitHub-only ownership boundary.
for forbidden in (
    "GitOperationJournalService",
    "GitOperationRecoveryService",
    "GitRepositorySnapshotService",
    "GitChangeTransferService",
    "GitLineTransferService",
    "GitChangesView",
    "GitW",
    "HospitalW",
    "git -C",
    "GitHubWorkItemsService",
    "GitHubWorkItemsView",
):
    if forbidden in service:
        errors.append(
            f"review-thread lifecycle ownership boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO PR REVIEW THREAD LIFECYCLE CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO PR REVIEW THREAD LIFECYCLE CONTRACTS // PASS")
print("checked guarded reply/resolve/unresolve review-thread actions")
