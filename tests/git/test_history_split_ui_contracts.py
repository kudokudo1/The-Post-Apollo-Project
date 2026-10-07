#!/usr/bin/env python3
"""Focused contracts for file Split in HISTORY Surgery."""

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


SPLIT = "widgets/GitHistorySplitView.qml"
SURGERY = "widgets/GitHistorySurgeryView.qml"
HISTORY = "widgets/GitHistoryView.qml"
GITW = "widgets/GitW.qml"

require(
    SPLIT,
    "required property var splitService",
    "Split view must use the guarded Split backend",
)
require(
    SPLIT,
    "splitService.preview(targetInput.text.trim())",
    "Split preview must delegate to the backend",
)
require(
    SPLIT,
    "splitService.toggleFirst(",
    "file rows must move between first and second replacement commits",
)
require(
    SPLIT,
    "splitService.setFirstMessage(",
    "first replacement message must belong to the backend plan",
)
require(
    SPLIT,
    "splitService.setSecondMessage(",
    "second replacement message must belong to the backend plan",
)
require(
    SPLIT,
    "splitService.arm()",
    "Split must expose explicit ARM",
)
require(
    SPLIT,
    "splitService.executeArmed()",
    "Split execution must use the exact armed backend plan",
)
require_regex(
    SPLIT,
    r"enabledAction:\s*"
    r"splitService\.armed.*"
    r"!splitService\.previewBusy.*"
    r"!splitService\.executionBusy",
    "Split execute must require an armed idle plan",
)
require(
    SPLIT,
    "FILE // LIVE",
    "first Split slice must identify file scope as live",
)
require(
    SPLIT,
    "HUNK // LATER",
    "hunk Split must remain explicitly deferred",
)
require(
    SPLIT,
    "LINE // LATER",
    "line Split must remain explicitly deferred",
)
require(
    SPLIT,
    "replacement tree = original target tree",
    "Split UI must communicate target-tree conservation",
)
require(
    SPLIT,
    "final tree = original HEAD tree",
    "Split UI must communicate final-tree conservation",
)
require(
    SPLIT,
    "OPERATIONS UNDO RESTORES THE EXACT PRE-SPLIT HEAD",
    "Split must communicate guarded rewrite Undo",
)

require(
    SURGERY,
    "required property var splitService",
    "Surgery must accept Split backend",
)
require(
    SURGERY,
    'label: "SPLIT"',
    "Split must be a live Surgery mode",
)
require(
    SURGERY,
    'onTriggered: root.surgeryMode = "split"',
    "Surgery selector must navigate to Split",
)
require_regex(
    SURGERY,
    r"GitHistorySplitView \{.*"
    r'visible: root\.surgeryMode === "split".*'
    r"splitService: root\.splitService",
    "Surgery must host Split alongside Fold and Absorb",
)

require(
    HISTORY,
    "property var historySplitService: null",
    "HISTORY must accept shared Split service",
)
require_regex(
    HISTORY,
    r"GitHistorySurgeryView \{.*"
    r"splitService: root\.historySplitService",
    "HISTORY Surgery must receive Split",
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
    r"GitHistoryView \{.*"
    r"historySplitService: historySplitService",
    "GitW must pass Split into HISTORY",
)

print("Git HISTORY Surgery Split UI contracts: PASS")
