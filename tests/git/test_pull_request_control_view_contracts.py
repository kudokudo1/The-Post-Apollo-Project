#!/usr/bin/env python3
"""Contracts for the standalone GitHub pull-request control surface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEW = ROOT / "widgets/GitHubPullRequestControlView.qml"
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


if not VIEW.exists():
    errors.append("missing widgets/GitHubPullRequestControlView.qml")
    view = ""
else:
    view = VIEW.read_text(encoding="utf-8")


# Dependency-injected standalone boundary.
for needle, label in (
    ("required property var lifecycleService", "PR lifecycle injection"),
    ("required property var queueProvider", "queue provider injection"),
    ("required property var queueLifecycleService", "queue lifecycle injection"),
    ("required property var threadProvider", "thread provider injection"),
    ("required property var threadLifecycleService", "thread lifecycle injection"),
    ('property string mode: "control"', "standalone mode state"),
):
    require(view, needle, label)

# Three first-class modes should exist without modifying GitW/WorkItems.
for mode in ('"control"', '"queue"', '"threads"'):
    require(view, mode, f"mode {mode}")

# Ordinary PR lifecycle controls.
for needle, label in (
    ("markReady(", "draft to ready"),
    ("convertToDraft(", "ready to draft"),
    ("editPullRequest(", "title/body/base edit"),
    ("updateLabels(", "labels"),
    ("updateAssignees(", "assignees"),
    ("updateReviewers(", "reviewers"),
    ("setMilestone(", "milestone"),
    ("clearMilestone(", "clear milestone"),
    ("commentPullRequest(", "PR comment"),
    ("reviewPullRequest(", "PR review"),
    ("closePullRequest(", "close"),
    ("reopenPullRequest(", "reopen"),
    ("updateBranch(", "branch update"),
    ("mergePullRequest(", "merge modes"),
):
    require(view, needle, label)

# Dangerous ordinary PR operations receive an additional UI arming layer.
for needle, label in (
    ('root.armOrRun(\n                            "update-branch"', "update arm"),
    ('root.armOrRun(\n                                "close"', "close arm"),
    ('"merge-" + modelData', "merge arm"),
    ("pullRequestHeadSha", "head pin surfaced"),
):
    require(view, needle, label)

# Merge queue exposes preview first, then execution, and keeps queue-jump out.
for needle, label in (
    ("previewEnqueue(", "enqueue preview"),
    ("previewDequeue(", "dequeue preview"),
    ("executeEnqueue()", "enqueue execute"),
    ("executeDequeue(", "dequeue execute"),
    ("entryForPullRequest(", "selected PR queue facts"),
):
    require(view, needle, label)

if "jump" in view.lower():
    errors.append("PR control view must not expose queue jumping")

# Review threads expose the actual conversation and guarded action service.
for needle, label in (
    ("threadProvider.threads", "thread list"),
    ("selectedThread.comments", "thread comments"),
    ("replyToThread(", "thread reply"),
    ("resolveThread(", "thread resolve"),
    ("unresolveThread(", "thread unresolve"),
    ("viewerCanReply", "reply permission"),
    ("viewerCanResolve", "resolve permission"),
    ("viewerCanUnresolve", "unresolve permission"),
    ("threadsTruncated", "bounded thread truth"),
    ("commentsTruncated", "bounded comment truth"),
):
    require(view, needle, label)

# Successful mutations refresh their read providers through neutral service
# signals instead of reaching into shared GitHubWorkItems/GitW architecture.
for needle, label in (
    ("function onQueueChanged(", "queue refresh handoff"),
    ("function onThreadChanged(", "thread refresh handoff"),
    ("function onMutationFinished(", "lifecycle completion handoff"),
    ("function refreshFacts()", "standalone refresh"),
):
    require(view, needle, label)

# Fresh shared seams remain outside this component.
for forbidden in (
    "GitW",
    "GitHubWorkItemsView",
    "GitHistoryView",
    "GitInteractiveRebaseView",
    "GitOperationRecoveryService",
    "GitChangeTransferService",
    "GitLineTransferService",
    "HospitalW",
    "GitHubProjectsService",
):
    if forbidden in view:
        errors.append(
            f"PR control view ownership boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO PR CONTROL VIEW CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO PR CONTROL VIEW CONTRACTS // PASS")
print("checked standalone CONTROL / QUEUE / THREADS pull-request surface")
