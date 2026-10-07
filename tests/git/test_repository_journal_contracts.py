#!/usr/bin/env python3
"""Focused contracts for journaled Git Repository mutations."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


def require_regex(path: str, pattern: str, message: str) -> None:
    text = read(path)
    assert re.search(pattern, text, re.S), f"{message}: {path}"


SERVICE = "services/git/GitRepositoryService.qml"

require(
    SERVICE,
    "property var operationJournal: null",
    "Repository service must accept the shared operation journal",
)
require(
    SERVICE,
    "property var snapshotService: null",
    "Repository service must accept the shared snapshot service",
)
require_regex(
    SERVICE,
    r"function shouldJournalOperation\(operation\).*"
    r'op !== "check-remote-tag".*'
    r'op !== "fsck"',
    "read-only repository diagnostics must stay outside mutation history",
)
require_regex(
    SERVICE,
    r"function runAction\(operation, a, b, c, d\).*"
    r'snapshotPhase = "BEFORE";.*'
    r'snapshotService\.capture\(',
    "journaled Repository actions must request a BEFORE snapshot",
)
require_regex(
    SERVICE,
    r'if \(root\.snapshotPhase === "BEFORE"\).*'
    r'operationJournal\.beginOperation\(.*'
    r'"REPOSITORY/".*'
    r'root\.executePendingAction\(\)',
    "Repository mutation execution must wait for snapshot + journal start",
)
require_regex(
    SERVICE,
    r"function maybeFinishAction\(\).*"
    r'snapshotPhase = "AFTER";.*'
    r'snapshotService\.capture\(',
    "Repository mutations must capture AFTER state before journal completion",
)
require(
    SERVICE,
    "operationJournal.completeOperation(",
    "successful Repository mutations must close their journal record",
)
require(
    SERVICE,
    "operationJournal.failOperation(",
    "failed Repository mutations must be retained in the journal",
)
require_regex(
    SERVICE,
    r"function journalSnapshot\(snapshot\).*"
    r'out\.recoveryClass = "EVIDENCE_ONLY".*'
    r"REPOSITORY OPERATION STATE IS NOT FULLY CAPTURED",
    "uncaptured repository domains must downgrade recovery claims",
)

for operation in (
    "add-remote",
    "rename-remote",
    "remove-remote",
    "set-url",
    "set-push-url",
    "set-fetchspec",
    "set-pushspec",
    "delete-remote-branch",
    "push-tag",
    "push-tags",
    "delete-remote-tag",
    "set-config",
    "unset-config",
    "submodule-sync",
    "hook-enable",
    "hook-disable",
    "worktree-prune",
    "worktree-lock",
    "worktree-unlock",
    "gc-auto",
    "maintenance",
):
    require(
        SERVICE,
        f'"{operation}"',
        f"{operation} must be classified explicitly for evidence-only recovery",
    )

for operation in (
    "fetch",
    "prune-remote",
    "create-tag-light",
    "create-tag-annotated",
    "create-tag-signed",
    "delete-tag",
    "submodule-update",
    "append-file-line",
    "remove-file-line",
    "replace-file-line",
):
    require(
        SERVICE,
        f'"{operation}"',
        f"{operation} must remain visible in the repository mutation dispatcher",
    )

require_regex(
    "widgets/GitW.qml",
    r"GitRepositoryService \{.*"
    r"id: repositoryService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must inject shared journal + snapshots into Repository service",
)

print("Git Repository journal contracts: PASS")
