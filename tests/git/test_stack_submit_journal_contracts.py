#!/usr/bin/env python3
"""Focused contracts for journaled Git stack submission."""

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


SERVICE = "services/git/GitStackSubmitService.qml"

require(
    SERVICE,
    "property var operationJournal: null",
    "Stack submit must accept the shared operation journal",
)
require(
    SERVICE,
    "property var snapshotService: null",
    "Stack submit must accept the shared snapshot service",
)
require_regex(
    SERVICE,
    r"function journalSnapshot\(snapshot\).*"
    r'out\.recoveryClass = "EVIDENCE_ONLY".*'
    r"STACK SUBMIT MUTATES REMOTE REFS \+ GITHUB PR STATE",
    "stack submit must never claim local-snapshot recovery for remote mutations",
)
require_regex(
    SERVICE,
    r"function submitArmed\(\).*"
    r'snapshotPhase = "BEFORE";.*'
    r'snapshotService\.capture\(',
    "stack submission must request a BEFORE snapshot",
)
require_regex(
    SERVICE,
    r'if \(root\.snapshotPhase === "BEFORE"\).*'
    r'operationJournal\.beginOperation\(.*'
    r'"STACK/SUBMIT".*'
    r'root\.startPendingSubmission\(\)',
    "stack submission must wait for snapshot + journal start",
)
require_regex(
    SERVICE,
    r"function maybeFinishSubmit\(\).*"
    r'snapshotPhase = "AFTER";.*'
    r'snapshotService\.capture\(',
    "stack submission must capture AFTER state before journal completion",
)
require(
    SERVICE,
    "operationJournal.completeOperation(",
    "successful stack submissions must close their journal record",
)
require(
    SERVICE,
    "operationJournal.failOperation(",
    "failed stack submissions must close their journal record",
)
require(
    SERVICE,
    "STACK SUBMIT TIMEOUT // REMOTE + PR STATE UNCERTAIN",
    "stack submit timeout must be journaled as uncertain remote state",
)
require(
    SERVICE,
    'git -C "$repo" push --atomic "${leases[@]}"',
    "stack submit must retain atomic push semantics",
)
require(
    SERVICE,
    "--force-with-lease=refs/heads/$branch:$expected_remote",
    "stack submit must retain exact remote lease guards",
)
require_regex(
    "widgets/GitW.qml",
    r"GitStackSubmitService \{.*"
    r"id: stackSubmitService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must inject shared journal + snapshots into stack submission",
)

print("Git stack submit journal contracts: PASS")
