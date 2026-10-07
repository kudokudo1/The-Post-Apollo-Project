#!/usr/bin/env python3
"""Focused contracts for staged Absorb in HISTORY Surgery."""

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


ABSORB = "widgets/GitHistoryAbsorbView.qml"
SURGERY = "widgets/GitHistorySurgeryView.qml"
HISTORY = "widgets/GitHistoryView.qml"
GITW = "widgets/GitW.qml"

require(
    ABSORB,
    "required property var absorbService",
    "Absorb view must use the staged Absorb backend",
)
require(
    ABSORB,
    "absorbService.preview(targetInput.text.trim())",
    "Absorb preview must use the backend",
)
require(
    ABSORB,
    "absorbService.arm()",
    "Absorb must expose explicit ARM",
)
require(
    ABSORB,
    "absorbService.executeArmed()",
    "Absorb execution must use the exact armed plan",
)
require_regex(
    ABSORB,
    r"enabledAction:\s*"
    r"absorbService\.armed.*"
    r"!absorbService\.previewBusy.*"
    r"!absorbService\.executionBusy",
    "Absorb execute must require an armed idle plan",
)
require(
    ABSORB,
    "USE SELECTED",
    "Absorb must accept the selected History commit as target",
)
require(
    ABSORB,
    "STAGE TRACKED CHANGES, THEN PREVIEW",
    "Absorb must communicate staged-input semantics",
)
require(
    ABSORB,
    "RESTORE OLD HEAD + EXACT STAGED PATCH",
    "Absorb must communicate its content-preserving Undo contract",
)
require(
    ABSORB,
    "FIXUP + AUTOSQUASH",
    "Absorb UI must describe its rehearsal model",
)

require(
    SURGERY,
    "required property var absorbService",
    "Surgery must accept the Absorb backend",
)
require(
    SURGERY,
    'label: "ABSORB"',
    "Absorb must be a live Surgery mode",
)
require(
    SURGERY,
    'selectedAction: root.mode === "absorb"',
    "Surgery must show Absorb selection state",
)
require(
    SURGERY,
    'onTriggered: root.mode = "absorb"',
    "Surgery must navigate to Absorb",
)
require_regex(
    SURGERY,
    r"GitHistoryAbsorbView \{.*"
    r'visible: root\.mode === "absorb".*'
    r"absorbService: root\.absorbService",
    "Surgery must host Absorb without replacing Fold",
)
require(
    SURGERY,
    'label: "SPLIT"',
    "Split must be a live Surgery mode",
)
require(
    SURGERY,
    'selectedAction: root.mode === "split"',
    "Surgery must expose Split selection state",
)

require(
    HISTORY,
    "property var historyAbsorbService: null",
    "HISTORY must accept the Absorb service",
)
require_regex(
    HISTORY,
    r"GitHistorySurgeryView \{.*"
    r"foldService: root\.historyFoldService.*"
    r"splitService: root\.historySplitService.*"
    r"absorbService: root\.historyAbsorbService",
    "HISTORY Surgery must receive Fold, Split, and Absorb",
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
    r"historyAbsorbService: historyAbsorbService",
    "GitW must pass Absorb into HISTORY",
)

print("Git HISTORY Surgery Absorb UI contracts: PASS")
