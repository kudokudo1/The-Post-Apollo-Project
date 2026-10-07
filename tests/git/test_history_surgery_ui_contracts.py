#!/usr/bin/env python3
"""Focused contracts for HISTORY Surgery / Fold integration."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

# Fold, file-group Split, and staged Absorb are live History Surgery organs.


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
    "required property var splitService",
    "Surgery surface must accept the Split backend",
)
require(
    VIEW,
    "required property var splitPatchService",
    "Surgery surface must accept the hunk Split backend",
)
require(
    VIEW,
    'label: "SPLIT"',
    "Split must be a live Surgery mode",
)
require(
    VIEW,
    'onTriggered: root.mode = "split"',
    "Surgery mode selector must open Split",
)
require_regex(
    VIEW,
    r"GitHistorySplitHubView \{.*"
    r'visible: root\.mode === "split".*'
    r"fileService: root\.splitService.*"
    r"hunkService: root\.splitPatchService",
    "Surgery must host the File/Hunk Split hub without replacing Fold",
)
require(
    VIEW,
    "required property var absorbService",
    "Surgery surface must accept the Absorb backend",
)
require(
    VIEW,
    'label: "ABSORB"',
    "Absorb must be a live Surgery mode",
)
require(
    VIEW,
    'selectedAction: root.mode === "absorb"',
    "Surgery must show Absorb selection state",
)
require(
    VIEW,
    'onTriggered: root.mode = "absorb"',
    "Surgery mode selector must open Absorb",
)
require_regex(
    VIEW,
    r"GitHistoryAbsorbView \{.*"
    r'visible: root\.mode === "absorb".*'
    r"absorbService: root\.absorbService",
    "Surgery must host Absorb without replacing Fold or Split",
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
require(
    HISTORY,
    "property var historySplitService: null",
    "HISTORY must accept the shared Split service",
)
require(
    HISTORY,
    "property var historySplitPatchService: null",
    "HISTORY must accept the shared hunk Split service",
)
require(
    HISTORY,
    "property var historyAbsorbService: null",
    "HISTORY must accept the shared Absorb service",
)
require_regex(
    HISTORY,
    r"GitHistorySurgeryView \{.*"
    r'visible: root\.subMode === "surgery".*'
    r"foldService: root\.historyFoldService.*"
    r"splitService: root\.historySplitService.*"
    r"splitPatchService: root\.historySplitPatchService.*"
    r"absorbService: root\.historyAbsorbService",
    "HISTORY must host Fold + Split + Absorb on the Surgery surface",
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
    r"GitHistorySplitService \{.*"
    r"id: historySplitService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must host Split with shared journal and snapshots",
)
require_regex(
    GITW,
    r"GitHistorySplitPatchService \{.*"
    r"id: historySplitPatchService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must host hunk Split with shared journal and snapshots",
)
require_regex(
    GITW,
    r"GitHistoryAbsorbService \{.*"
    r"id: historyAbsorbService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must host Absorb with shared journal and snapshots",
)
require_regex(
    GITW,
    r"GitHistoryView \{.*"
    r"historyFoldService: historyFoldService.*"
    r"historySplitService: historySplitService.*"
    r"historySplitPatchService: historySplitPatchService.*"
    r"historyAbsorbService: historyAbsorbService",
    "GitW must pass Fold + Split + Absorb into HISTORY",
)

print("Git HISTORY Surgery Fold + Split + Absorb UI contracts: PASS")
