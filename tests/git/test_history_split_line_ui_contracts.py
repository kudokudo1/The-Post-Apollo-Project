#!/usr/bin/env python3
"""Focused contracts for line-level Split Surgery UI."""

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


HUB = "widgets/GitHistorySplitHubView.qml"
LINE = "widgets/GitHistorySplitLineView.qml"
SURGERY = "widgets/GitHistorySurgeryView.qml"
HISTORY = "widgets/GitHistoryView.qml"
GITW = "widgets/GitW.qml"

require(
    LINE,
    "required property var lineService",
    "line Split UI must use the line backend",
)
require(
    LINE,
    "HISTORY SURGERY // SPLIT BY LINE",
    "line Split UI must identify its surgery scope",
)
require(
    LINE,
    "lineService.preview(",
    "line preview must use the guarded backend",
)
require(
    LINE,
    "lineService.setFirstLine(",
    "line edit rows must toggle between replacement parts",
)
require(
    LINE,
    "PART 1",
    "line UI must expose part 1",
)
require(
    LINE,
    "PART 2",
    "line UI must expose part 2",
)
require(
    LINE,
    "lineService.setMessages(",
    "line Split messages must update the backend plan",
)
require(
    LINE,
    "lineService.arm()",
    "line Split must expose explicit ARM",
)
require(
    LINE,
    "lineService.executeArmed()",
    "line Split execution must use the frozen plan",
)
require_regex(
    LINE,
    r"enabledAction:\s*"
    r"lineService\.armed.*"
    r"!lineService\.previewBusy.*"
    r"!lineService\.executionBusy",
    "line Split execute must require an armed idle plan",
)
require(
    LINE,
    "simple modified text paths only",
    "line UI must disclose its path-safety boundary",
)
require(
    LINE,
    "OPERATIONS UNDO RESTORES THE EXACT PRE-SPLIT BRANCH HEAD",
    "line UI must communicate guarded Undo",
)

require_regex(
    HUB,
    r"GitHistorySplitLineView \{.*"
    r'visible: root\.mode === "line".*'
    r"lineService: root\.lineService",
    "LINE mode must host the line Split view",
)
require(
    SURGERY,
    "lineService: root.splitLineService",
    "Surgery must pass line Split into the Split hub",
)
require(
    HISTORY,
    "property var historySplitLineService: null",
    "HISTORY must accept line Split",
)
require_regex(
    HISTORY,
    r"GitHistorySurgeryView \{.*"
    r"splitLineService: root\.historySplitLineService",
    "HISTORY must pass line Split into Surgery",
)
require_regex(
    GITW,
    r"GitHistorySplitLineService \{.*"
    r"id: historySplitLineService.*"
    r"operationJournal: operationJournalService.*"
    r"snapshotService: repositorySnapshotService",
    "GitW must instantiate line Split with shared journal and snapshots",
)
require_regex(
    GITW,
    r"GitHistoryView \{.*"
    r"historySplitLineService: historySplitLineService",
    "GitW must pass line Split into HISTORY",
)

print("Git HISTORY line Split UI contracts: PASS")
