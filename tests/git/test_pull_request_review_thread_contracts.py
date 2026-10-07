#!/usr/bin/env python3
"""Focused contracts for the read-only GitHub PR review-thread provider."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/github/GitHubPullRequestReviewThreadProvider.qml"
errors = []


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


if not SERVICE.exists():
    errors.append("missing GitHubPullRequestReviewThreadProvider.qml")
    service = ""
else:
    service = SERVICE.read_text(encoding="utf-8")


for function_name in (
    "normalizeRepository",
    "normalizePullRequestNumber",
    "threadAt",
    "threadsForPath",
    "unresolvedThreads",
    "countWhere",
    "normalizeComment",
    "normalizeThread",
    "parseResponse",
    "refresh",
    "maybeFinish",
):
    require(
        service,
        f"function {function_name}(",
        f"review-thread provider must expose {function_name}",
    )

# The provider must read native review threads, not flatten reviews or issue
# comments into an approximation.
require(
    service,
    "reviewThreads(first:$threadLimit)",
    "provider must read PullRequest.reviewThreads",
)
for needle, label in (
    ("isResolved", "resolved state"),
    ("isOutdated", "outdated state"),
    ("isCollapsed", "collapsed state"),
    ("path line originalLine startLine originalStartLine", "thread location"),
    ("diffSide startDiffSide subjectType", "thread diff/subject facts"),
    ("viewerCanReply viewerCanResolve viewerCanUnresolve", "viewer permissions"),
    ("resolvedBy{login}", "resolver identity"),
):
    require(service, needle, label)

# Thread comments retain stable identity, authorship, body, time, diff context,
# current/original location, and review lineage.
for needle, label in (
    ("id fullDatabaseId body bodyText resourcePath", "comment identity/body"),
    ("author{login avatarUrl url}", "comment author"),
    ("authorAssociation state createdAt updatedAt publishedAt", "comment metadata"),
    ("path line originalLine startLine originalStartLine diffHunk outdated", "comment location"),
    ("commit{oid} originalCommit{oid}", "comment commit provenance"),
    ("replyTo{id fullDatabaseId}", "reply lineage"),
    ("pullRequestReview{id state author{login}}", "review lineage"),
):
    require(service, needle, label)

# Prefer GitHub's newer 64-bit-safe identity instead of the deprecated
# databaseId field.
require(
    service,
    "fullDatabaseId",
    "comment provider must retain fullDatabaseId",
)
if " databaseId" in service or "{databaseId" in service:
    errors.append("deprecated databaseId must not be queried")

# Keep explicit counts useful to PULLS and Hospital without inventing
# interpretation such as NEEDS_ME.
for needle, label in (
    ("readonly property int unresolvedCount", "unresolved count"),
    ("readonly property int resolvedCount", "resolved count"),
    ("readonly property int outdatedCount", "outdated count"),
    ("readonly property int activeUnresolvedCount", "active unresolved count"),
    ("readonly property int replyableCount", "replyable count"),
    ("readonly property int resolvableCount", "resolvable count"),
    ('? !row.isResolved && !row.isOutdated', "active unresolved definition"),
):
    require(service, needle, label)

# Surface truncation truthfully when the bounded read cannot contain every
# thread/comment.
for needle, label in (
    ("property int maxThreads: 100", "bounded thread read"),
    ("property int maxCommentsPerThread: 100", "bounded comment read"),
    ("property bool threadsTruncated: false", "thread truncation state"),
    ("property bool commentsTruncated: false", "comment truncation state"),
    ("pageInfo{hasNextPage endCursor}", "pagination evidence"),
):
    require(service, needle, label)

# Read-only ownership boundary. Actions belong in a later lifecycle service;
# local Git, Hospital, and shared GitW integration are forbidden here.
for forbidden in (
    "resolveReviewThread",
    "unresolveReviewThread",
    "reply_to_review_comment",
    "replyToReviewComment",
    "addPullRequestReviewComment",
    "GitOperationJournalService",
    "GitOperationRecoveryService",
    "GitRepositorySnapshotService",
    "GitChangeTransferService",
    "GitLineTransferService",
    "GitChangesView",
    "GitW",
    "HospitalW",
    "git -C",
    "gh pr review",
    "gh pr comment",
):
    if forbidden in service:
        errors.append(
            f"review-thread provider ownership boundary violated by {forbidden!r}"
        )

if errors:
    print("POST-APOLLO PR REVIEW THREAD CONTRACTS // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("POST-APOLLO PR REVIEW THREAD CONTRACTS // PASS")
print("checked native read-only pull-request review thread provider")
