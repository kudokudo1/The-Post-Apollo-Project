#!/usr/bin/env python3
"""Focused contracts for hunk-level Split Surgery UI."""

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
HUNK = "widgets/GitHistorySplitHunkView.qml"

require(
    HUB,
    "required property var fileService",
    "Split hub must preserve file Split",
)
require(
    HUB,
    "required property var hunkService",
    "Split hub must accept hunk Split",
)
require(
    HUB,
    'label: "FILE"',
    "Split hub must expose FILE mode",
)
require(
    HUB,
    'label: "HUNK"',
    "Split hub must expose HUNK mode",
)
require(
    HUB,
    "required property var lineService",
    "Split hub must accept line Split",
)
require(
    HUB,
    'label: "LINE"',
    "Split hub must expose LINE mode",
)
require(
    HUB,
    'selectedAction: root.mode === "line"',
    "Split hub must show LINE selection state",
)
require(
    HUB,
    'onTriggered: root.mode = "line"',
    "Split hub must navigate to line Split",
)
require_regex(
    HUB,
    r"GitHistorySplitView \{.*"
    r'visible: root\.mode === "file".*'
    r"splitService: root\.fileService",
    "FILE mode must preserve the existing Split view",
)
require_regex(
    HUB,
    r"GitHistorySplitHunkView \{.*"
    r'visible: root\.mode === "hunk".*'
    r"hunkService: root\.hunkService",
    "HUNK mode must host the hunk Split view",
)

require(
    HUNK,
    "required property var hunkService",
    "hunk UI must use the patch Split backend",
)
require(
    HUNK,
    "HISTORY SURGERY // SPLIT BY HUNK",
    "hunk UI must identify its surgery scope",
)
require(
    HUNK,
    "hunkService.preview(",
    "hunk preview must use the backend",
)
require(
    HUNK,
    "hunkService.setFirstHunk(",
    "hunk rows must toggle between replacement parts",
)
require(
    HUNK,
    "PART 1",
    "hunk UI must expose part 1",
)
require(
    HUNK,
    "PART 2",
    "hunk UI must expose part 2",
)
require(
    HUNK,
    "hunkService.setMessages(",
    "hunk Split messages must update the backend plan",
)
require(
    HUNK,
    "hunkService.arm()",
    "hunk Split must expose ARM",
)
require(
    HUNK,
    "hunkService.executeArmed()",
    "hunk Split execution must use the frozen plan",
)
require_regex(
    HUNK,
    r"enabledAction:\s*"
    r"hunkService\.armed.*"
    r"!hunkService\.previewBusy.*"
    r"!hunkService\.executionBusy",
    "hunk Split execute must require an armed idle plan",
)
require(
    HUNK,
    "binary / rename / copy paths refused",
    "hunk UI must disclose unsupported path types",
)
require(
    HUNK,
    "OPERATIONS UNDO RESTORES THE EXACT PRE-SPLIT HEAD",
    "hunk UI must communicate guarded Undo",
)

print("Git HISTORY hunk Split UI contracts: PASS")
