#!/usr/bin/env python3
"""Focused contracts for journaled Git stack restacks."""

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


SERVICE = "services/git/GitStackExecutor.qml"

require(
    SERVICE,
    "property var operationJournal: null",
    "Stack executor must accept the shared operation journal",
)
require(
    SERVICE,
    "property var snapshotService: null",
    "Stack executor must accept the shared snapshot service",
)
require_regex(
    SERVICE,
    r"function executeArmed\(\).*"
    r'snapshotPhase = "BEFORE";.*'
    r'snapshotService\.capture\(',
    "restack execution must request a BEFORE snapshot",
)
require_regex(
    SERVICE,
    r'if \(root\.snapshotPhase === "BEFORE"\).*'
    r'operationJournal\.beginOperation\(.*'
    r'"STACK/RESTACK".*'
    r'root\.startPendingExecution\(\)',
    "restack process must wait for snapshot + journal start",
)
require_regex(
    SERVICE,
    r"function maybeFinish\(\).*"
    r'snapshotPhase = "AFTER";.*'
    r'snapshotService\.capture\(',
    "restack must capture AFTER state before journal completion",
)
require(
    SERVICE,
    "operationJournal.completeOperation(",
    "successful restacks must close their journal record",
)
require(
    SERVICE,
    "operationJournal.failOperation(",
    "failed restacks must close their journal record",
)
require(
    SERVICE,
    'recoveryClass: "EVIDENCE_ONLY"',
    "uncertain restack timeout state must never claim automatic recovery",
)
require(
    SERVICE,
    "RESTACK TIMEOUT // REPOSITORY STATE UNCERTAIN",
    "timeout must be recorded explicitly in the operation journal",
)
require(
    SERVICE,
    'printf "update refs/heads/%s %s %s',
    "restack must retain guarded expected-old ref updates",
)
require(
    SERVICE,
    '} | git -C "$repo" update-ref --stdin',
    "restack branch movement must remain one atomic ref transaction",
)
require_regex(
    "widgets/GitW.qml",
    r"GitStackExecutor \{.*"
    r"id: stackExecutor.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must inject shared journal + snapshots into stack restack",
)

print("Git stack journal contracts: PASS")
