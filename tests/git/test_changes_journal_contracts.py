#!/usr/bin/env python3
"""Focused contracts for journaled Git Changes mutations."""

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


SERVICE = "services/git/GitChangesService.qml"

require(
    SERVICE,
    "property var operationJournal: null",
    "Changes service must accept the shared operation journal",
)
require(
    SERVICE,
    "property var snapshotService: null",
    "Changes service must accept the shared snapshot service",
)
require_regex(
    SERVICE,
    r"function journalSnapshot\(snapshot\).*"
    r'out\.recoveryClass = "EVIDENCE_ONLY".*'
    r"CHANGES CONTENT IS NOT YET PRESERVED FOR AUTOMATIC RECOVERY",
    "Changes mutations must not claim automatic recovery before patch preservation exists",
)
require_regex(
    SERVICE,
    r"function runAction\(operation, a, b, c, d\).*"
    r'snapshotPhase = "BEFORE";.*'
    r'snapshotService\.capture\(',
    "Changes mutations must request a BEFORE snapshot",
)
require_regex(
    SERVICE,
    r'if \(root\.snapshotPhase === "BEFORE"\).*'
    r'operationJournal\.beginOperation\(.*'
    r'"CHANGES/".*'
    r'root\.executePendingAction\(\)',
    "Changes mutation execution must wait for snapshot + journal start",
)
require_regex(
    SERVICE,
    r"function maybeFinishAction\(\).*"
    r'snapshotPhase = "AFTER";.*'
    r'snapshotService\.capture\(',
    "Changes mutations must capture AFTER state before journal completion",
)
require(
    SERVICE,
    "operationJournal.completeOperation(",
    "successful Changes mutations must close their journal record",
)
require(
    SERVICE,
    "operationJournal.failOperation(",
    "failed Changes mutations must be retained in the journal",
)

for operation in (
    "stage",
    "unstage",
    "stage-all",
    "unstage-all",
    "commit",
    "stash",
    "stash-apply",
    "stash-pop",
    "stash-drop",
    "discard-file",
    "resolve-ours",
    "resolve-theirs",
    "mark-resolved",
    "continue-operation",
    "abort-operation",
    "skip-operation",
    "stage-line",
    "unstage-line",
    "discard-line",
    "stage-hunk",
    "unstage-hunk",
    "discard-hunk",
):
    require(
        SERVICE,
        f'"{operation}"',
        f"{operation} must remain in the centralized Changes mutation dispatcher",
    )

require_regex(
    "widgets/GitW.qml",
    r"GitChangesService \{.*"
    r"id: changesService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must inject shared journal + snapshots into Changes",
)

print("Git Changes journal contracts: PASS")
