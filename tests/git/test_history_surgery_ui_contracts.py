#!/usr/bin/env python3
"""Focused contracts for HISTORY Surgery / Fold integration."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

# Fold is the first live History Surgery organ. Absorb and Split are layered
# on stacked follow-up branches so each surgery primitive can land independently.


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


def require_regex(path: str, pattern: str, message: str) -> None:
    text = read(path)
    assert re.search(pattern, text, re.S), f"{message}: {path}"


VIEW = "widgets/GitHistorySurgeryView.qml"
HISTORY = "widgets/GitHistoryView.qml"
GITW = "widgets/GitW.qml"

require(
    VIEW,
    "required property var foldService",
    "Surgery surface must use the Fold backend",
)
require(
    VIEW,
    'label: "FOLD"',
    "Fold must be the live first Surgery mode",
)
require(
    VIEW,
    'label: "SPLIT // NEXT"',
    "Split must remain visibly unavailable until implemented",
)
require(
    VIEW,
    'label: "ABSORB // NEXT"',
    "Absorb must remain visibly unavailable until implemented",
)
require(
    VIEW,
    "foldService.preview(",
    "Fold preview must go through the guarded backend",
)
require(
    VIEW,
    "foldService.setMessage(",
    "Fold message edits must update the backend plan",
)
require(
    VIEW,
    "foldService.arm()",
    "Fold must expose explicit ARM",
)
require(
    VIEW,
    "foldService.executeArmed()",
    "Fold execution must use the exact armed backend plan",
)
require_regex(
    VIEW,
    r"enabledAction:\s*"
    r"foldService\.armed.*"
    r"!foldService\.previewBusy.*"
    r"!foldService\.executionBusy",
    "Fold execution must require an armed idle plan",
)
require(
    VIEW,
    "USE SELECTED AS OLDEST",
    "Surgery must accept the selected History commit as the oldest endpoint",
)
require(
    VIEW,
    "USE SELECTED AS NEWEST",
    "Surgery must accept the selected History commit as the newest endpoint",
)
require(
    VIEW,
    "OPERATIONS UNDO RESTORES THE EXACT PRE-FOLD BRANCH HEAD",
    "Fold UI must communicate guarded Undo semantics",
)

require_regex(
    HISTORY,
    r'key: "surgery".*'
    r'label: "SURGERY".*'
    r'color: Colors\.red',
    "SURGERY must be a first-class HISTORY submode",
)
require(
    HISTORY,
    "property var historyFoldService: null",
    "HISTORY must accept the shared Fold service",
)
require_regex(
    HISTORY,
    r"GitHistorySurgeryView \{.*"
    r'visible: root\.subMode === "surgery".*'
    r"foldService: root\.historyFoldService",
    "HISTORY must host the Surgery surface",
)

require_regex(
    GITW,
    r"GitHistoryFoldService \{.*"
    r"id: historyFoldService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must host Fold with shared journal and snapshots",
)
require_regex(
    GITW,
    r"GitHistoryView \{.*"
    r"historyFoldService: historyFoldService",
    "GitW must pass Fold into HISTORY",
)

print("Git HISTORY Surgery Fold UI contracts: PASS")
