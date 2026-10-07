#!/usr/bin/env python3
"""Focused contracts for guarded GitHub merge queue mutations."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/github/GitHubMergeQueueLifecycleService.qml"
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


if not SERVICE.exists():
    errors.append("missing GitHubMergeQueueLifecycleService.qml")
    service = ""
else:
    service = SERVICE.read_text(encoding="utf-8")


for function_name in (
    "previewEnqueue",
    "previewDequeue",
    "executeEnqueue",
    "executeDequeue",
    "startMutation",
    "startVerify",
):
    require(
        service,
        f"function {function_name}(",
        f"merge queue lifecycle must expose {function_name}",
    )

# Preflight must identify the PR, pin the head for enqueue, and verify that the
# base branch actually has a native GitHub merge queue.
for needle, label in (
    ("pullRequest(number:$number)", "PR preflight"),
    ("mergeQueue(branch:$branch)", "native queue preflight"),
    ("state isDraft headRefOid baseRefName", "PR state/head/base evidence"),
    ("PULL REQUEST IS NOT OPEN", "closed PR refusal"),
    ("DRAFT PULL REQUEST CANNOT ENTER MERGE QUEUE", "draft refusal"),
    ("PULL REQUEST HEAD MOVED", "stale head refusal"),
    ("NATIVE MERGE QUEUE NOT CONFIGURED", "missing queue refusal"),
):
    require(service, needle, label)

# Enqueue is pinned to the previewed head and must never use queue-jump mode in
# this first safe slice.
require(
    service,
    "enqueuePullRequest(input:{pullRequestId:$pullRequestId,expectedHeadOid:$expectedHeadOid,jump:false})",
    "enqueue must use expectedHeadOid and ordinary queue position",
)
if "jump:true" in service:
    errors.append("queue jump must not be enabled in the initial lifecycle slice")

# GitHub's dequeue mutation expects the pull request node ID.
require(
    service,
    "dequeuePullRequest(input:{id:$id})",
    "dequeue must use the pull request node ID",
)
require(
    service,
    "DEQUEUE REFUSED // EXPLICIT CONFIRMATION REQUIRED",
    "dequeue must require explicit confirmation",
)

# Mutations are not considered verified until the PR's mergeQueueEntry is read
# back and matches the expected queued/dequeued state.
require(
    service,
    "mergeQueueEntry{id position state",
    "queue-entry evidence must be retained",
)
require(
    service,
    "PULL REQUEST HEAD MOVED DURING OPERATION",
    "post-mutation head identity must be verified",
)
require(
    service,
    "ENQUEUE NOT VISIBLE AFTER MUTATION",
    "enqueue verification must confirm queue membership",
)
require(
    service,
    "DEQUEUE NOT VISIBLE AFTER MUTATION",
    "dequeue verification must confirm queue removal",
)
require(
    service,
    "MUTATED // EVIDENCE UNVERIFIED",
    "post-mutation verification failure must remain truthful",
)
require(
    service,
    "signal queueChanged(",
    "service must expose neutral queue refresh handoff",
)
require(
    service,
    "signal mutationFinished(",
    "service must expose mutation/evidence completion",
)
require(
    service,
    "const timedOutPhase = root.phase;",
    "timeout routing must preserve the phase that timed out",
)
require(
    service,
    'if (timedOutPhase === "PREVIEW")',
    "preview timeout must stay on the preview-failure path",
)

# This backend owns GitHub merge-queue mutation only. No local Git surgery,
# Hospital interpretation, or shared UI integration belongs here.
for forbidden in (
    "GitOperationJournalService",
    "GitOperationRecoveryService",
    "GitRepositorySnapshotService",
    "GitBranchWorkspaceService",
    "GitChangeTransferService",
    "GitChangesView",
    "GitW",
    "HospitalW",
    "git -C",
    "gh pr merge",
):
    if forbidden in service:
        errors.append(
            f"merge queue lifecycle ownership boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO GITHUB MERGE QUEUE LIFECYCLE CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO GITHUB MERGE QUEUE LIFECYCLE CONTRACTS // PASS")
print("checked guarded enqueue/dequeue merge queue backend")
