#!/usr/bin/env python3
"""Focused contracts for the Git Operations / guarded Undo surface."""

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


require(
    "widgets/GitOperationsView.qml",
    "operationJournal.repositoryEntries",
    "Operations view must show repository-scoped journal entries",
)
require(
    "widgets/GitOperationsView.qml",
    "recoveryService.preview(selectedRecord)",
    "Operations view must use the backend's real non-mutating Undo preview",
)
require(
    "widgets/GitOperationsView.qml",
    "BEFORE → AFTER",
    "Operations view must expose repository-time transition evidence",
)
require(
    "widgets/GitOperationsView.qml",
    "EXECUTE GUARDED UNDO",
    "Operations view must label Undo as guarded execution",
)
require_regex(
    "widgets/GitOperationsView.qml",
    r"enabled:.*root\.selectedPreview\.allowed.*!root\.recoveryService\.busy",
    "Undo control must only enable for a currently allowed preview",
)
require_regex(
    "widgets/GitOperationsView.qml",
    r"root\.recoveryService\.execute\(.*root\.selectedRecord\.id.*root\.selectedRecord",
    "Operations view must execute recovery using the selected journal record",
)
require(
    "widgets/GitOperationsView.qml",
    'String(root.selectedPreview.reason || "")',
    "refused Undo must explain the backend refusal reason",
)
require(
    "widgets/GitW.qml",
    'root.gitView = "operations"',
    "GitW must expose an Operations camera",
)
require_regex(
    "widgets/GitW.qml",
    r"GitOperationsView \{.*operationJournal: operationJournalService.*recoveryService: operationRecoveryService",
    "Operations camera must use the shared journal and recovery backend",
)
require_regex(
    "widgets/GitW.qml",
    r'name: "OPERATIONS".*key: "operations".*symbol: "↶".*available: true',
    "Operations must be a first-class Git mode",
)
require_regex(
    "widgets/GitW.qml",
    r'=== "operations".*root\.showGitOperations\(\)',
    "Operations selector must navigate to the Operations camera",
)

print("Git operation UI contracts: PASS")
