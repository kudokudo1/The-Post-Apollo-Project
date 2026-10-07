#!/usr/bin/env python3
"""Focused contracts for file-group Split Surgery UI."""

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


VIEW = "widgets/GitHistorySplitView.qml"

require(
    VIEW,
    "required property var splitService",
    "Split UI must use the standalone backend",
)
require(
    VIEW,
    "HISTORY SURGERY // SPLIT BY FILE",
    "Split UI must identify the file-group slice",
)
require(
    VIEW,
    "splitService.preview(targetInput.text.trim())",
    "Split preview must go through the guarded backend",
)
require(
    VIEW,
    "splitService.setFirstFile(",
    "file rows must toggle between part 1 and part 2",
)
require(
    VIEW,
    "PART 1",
    "Split UI must expose the first file group",
)
require(
    VIEW,
    "PART 2",
    "Split UI must expose the second file group",
)
require(
    VIEW,
    "splitService.setMessages(",
    "replacement commit messages must update the backend plan",
)
require(
    VIEW,
    "splitService.arm()",
    "Split must expose explicit ARM",
)
require(
    VIEW,
    "splitService.executeArmed()",
    "Split execution must use the frozen backend plan",
)
require_regex(
    VIEW,
    r"enabledAction:\s*"
    r"splitService\.armed.*"
    r"!splitService\.previewBusy.*"
    r"!splitService\.executionBusy",
    "Split execution must require an armed idle plan",
)
require(
    VIEW,
    "STRICT FILE SPLIT SLICE",
    "UI must communicate the limits of this Split slice",
)
require(
    VIEW,
    "renames/copies refused for now",
    "UI must disclose unsupported rename/copy splitting",
)
require(
    VIEW,
    "OPERATIONS UNDO RESTORES THE EXACT PRE-SPLIT HEAD",
    "Split UI must communicate guarded Undo",
)

print("Git HISTORY Split UI contracts: PASS")
