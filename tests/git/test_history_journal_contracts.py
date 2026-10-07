#!/usr/bin/env python3
"""Focused contracts for journaled Git History mutations."""

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


SERVICE = "services/git/GitHistoryService.qml"

require(
    SERVICE,
    "property var operationJournal: null",
    "History service must accept the shared operation journal",
)
require(
    SERVICE,
    "property var snapshotService: null",
    "History service must accept the shared snapshot service",
)
require(
    SERVICE,
    'return String(operation || "") !== "copy-sha";',
    "clipboard-only COPY SHA must stay outside repository mutation history",
)
require_regex(
    SERVICE,
    r"function runAction\(operation, a, b, c\).*"
    r'snapshotPhase = "BEFORE";.*'
    r'snapshotService\.capture\(',
    "journaled History actions must request a BEFORE snapshot",
)
require_regex(
    SERVICE,
    r'if \(root\.snapshotPhase === "BEFORE"\).*'
    r'operationJournal\.beginOperation\(.*'
    r'"HISTORY/".*'
    r'root\.executePendingAction\(\)',
    "History mutation execution must wait for snapshot + journal start",
)
require_regex(
    SERVICE,
    r"function maybeFinishAction\(\).*"
    r'snapshotPhase = "AFTER";.*'
    r'snapshotService\.capture\(',
    "History mutations must capture AFTER state before journal completion",
)
require(
    SERVICE,
    "operationJournal.completeOperation(",
    "successful History mutations must close their journal record",
)
require(
    SERVICE,
    "operationJournal.failOperation(",
    "failed History mutations must be retained in the journal",
)
require(
    SERVICE,
    'recoveryClass: "EVIDENCE_ONLY"',
    "missing AFTER snapshots must downgrade recovery claims",
)

for operation in (
    "merge",
    "cherry-pick",
    "revert",
    "detach",
    "reset",
    "branch",
    "tag",
):
    require_regex(
        SERVICE,
        rf'return\s+runAction\(\s*"{re.escape(operation)}"',
        f"{operation} must flow through the History action seam",
    )

require(
    "widgets/GitHistoryView.qml",
    "ARM MERGE SELECTED INTO CURRENT",
    "History UI must expose an armed ordinary merge control",
)

require_regex(
    "widgets/GitW.qml",
    r"GitHistoryService \{.*"
    r"id: historyService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must inject the shared journal + snapshot services into History",
)

print("Git History journal contracts: PASS")
