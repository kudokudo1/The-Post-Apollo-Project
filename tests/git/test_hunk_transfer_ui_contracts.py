#!/usr/bin/env python3
"""Focused contracts for hunk-level change-transfer UI."""

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


PANEL = "widgets/GitChangeTransferView.qml"
CHANGES = "widgets/GitChangesView.qml"

require(
    PANEL,
    'property string transferScope: "file"',
    "shared transfer panel must expose scope",
)
require(
    PANEL,
    "property int hunkIndex: -1",
    "shared transfer panel must carry a selected hunk index",
)
require_regex(
    PANEL,
    r"readonly property bool previewMatchesSelection:.*"
    r"previewScope.*transferScope.*"
    r"transferScope !== \"hunk\".*"
    r"previewHunkIndex.*hunkIndex",
    "execute eligibility must match exact hunk scope/index",
)
require_regex(
    PANEL,
    r'if \(transferScope === "hunk"\).*'
    r'transferService\.previewHunk\(.*'
    r'selectedDestinationPath.*'
    r'filePath.*'
    r'hunkIndex.*'
    r'transferMode',
    "hunk PREVIEW must delegate to previewHunk",
)
require(
    PANEL,
    '"TRANSFER // HUNK "',
    "transfer panel must visibly identify hunk scope",
)
require_regex(
    CHANGES,
    r"function hunkTransferEligible\(\).*"
    r'root\.hunkMode === "worktree".*'
    r"root\.selectedHunkIndex >= 0.*"
    r"!root\.changesService\.hunkBusy",
    "hunk transfer must only be offered for a selected worktree hunk",
)
require_regex(
    CHANGES,
    r'function openTransfer\(scope\).*'
    r'requested === "hunk".*'
    r'root\.hunkTransferEligible\(\).*'
    r"root\.transferHunkIndex =.*"
    r"root\.selectedHunkIndex",
    "opening hunk transfer must freeze the selected hunk index",
)
require_regex(
    CHANGES,
    r'label: "TRANSFER".*'
    r"enabledAction: root\.hunkTransferEligible\(\).*"
    r'onTriggered: root\.openTransfer\("hunk"\)',
    "HUNKS controls must expose guarded transfer",
)
require_regex(
    CHANGES,
    r"GitChangeTransferView \{.*"
    r"transferScope: root\.transferScope.*"
    r"hunkIndex: root\.transferHunkIndex",
    "Changes must pass hunk scope/index into the shared transfer panel",
)

print("Git hunk transfer UI contracts: PASS")
