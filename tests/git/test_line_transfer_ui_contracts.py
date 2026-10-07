#!/usr/bin/env python3
"""Focused contracts for line-level change-transfer UI."""

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


PANEL = "widgets/GitLineTransferView.qml"
CHANGES = "widgets/GitChangesView.qml"

require(
    PANEL,
    "required property var lineTransferService",
    "line overlay must depend on the guarded line backend",
)
require(
    PANEL,
    "property int hunkIndex: -1",
    "line overlay must carry the frozen hunk index",
)
require(
    PANEL,
    "property int lineIndex: -1",
    "line overlay must carry the frozen line index",
)
require_regex(
    PANEL,
    r"readonly property bool previewMatchesSelection:.*"
    r"destinationPath.*selectedDestinationPath.*"
    r"transferMode.*transferMode.*"
    r"filePath.*filePath.*"
    r"hunkIndex.*hunkIndex.*"
    r"lineIndex.*lineIndex",
    "execute eligibility must match exact line preview identity",
)
require_regex(
    PANEL,
    r"lineTransferService\.preview\(.*"
    r"selectedDestinationPath.*"
    r"filePath.*"
    r"hunkIndex.*"
    r"lineIndex.*"
    r"transferMode",
    "line PREVIEW must delegate exact selection to the backend",
)
require(
    PANEL,
    'label: "MOVE"',
    "line overlay must expose MOVE",
)
require(
    PANEL,
    'label: "COPY"',
    "line overlay must expose COPY",
)
require_regex(
    PANEL,
    r'label:\s*lineTransferService\.previewBusy\s*'
    r'\? "PREVIEWING"\s*'
    r': "PREVIEW"',
    "line overlay must require explicit preview",
)
require(
    PANEL,
    "lineTransferService.execute()",
    "line EXECUTE must delegate to the guarded backend",
)
require(
    CHANGES,
    'import "../services/git"',
    "Changes must import the local line-transfer service type",
)
require_regex(
    CHANGES,
    r"GitLineTransferService \{.*"
    r"id: lineTransferService.*"
    r"operationJournal:.*root\.transferService.*operationJournal.*"
    r"snapshotService:.*root\.transferService.*snapshotService.*"
    r"repositoryPath:.*root\.gitService",
    "line backend must inherit the shared journal/snapshot/repository context",
)
require_regex(
    CHANGES,
    r"function lineTransferEligible\(\).*"
    r'root\.hunkMode === "worktree".*'
    r"root\.selectedHunkIndex >= 0.*"
    r"root\.selectedLineIndex >= 0.*"
    r"Boolean\(line\.selectable\).*"
    r"!lineTransferService\.transferBusy",
    "line transfer must only be offered for a selectable worktree diff line",
)
require_regex(
    CHANGES,
    r'function openTransfer\(scope\).*'
    r'token === "line".*'
    r'root\.lineTransferEligible\(\).*'
    r"root\.transferHunkIndex =.*root\.selectedHunkIndex.*"
    r"root\.transferLineIndex =.*root\.selectedLineIndex",
    "opening line transfer must freeze hunk and line identity",
)
require_regex(
    CHANGES,
    r'label: "TRANSFER".*'
    r"enabledAction: root\.lineTransferEligible\(\).*"
    r'onTriggered: root\.openTransfer\("line"\)',
    "line controls must expose guarded transfer",
)
require_regex(
    CHANGES,
    r"GitLineTransferView \{.*"
    r"lineTransferService: lineTransferService.*"
    r"hunkIndex: root\.transferHunkIndex.*"
    r"lineIndex: root\.transferLineIndex",
    "Changes must pass frozen line identity into the overlay",
)
require_regex(
    CHANGES,
    r"target: lineTransferService.*"
    r"function onTransferFinished\(success, detail\).*"
    r"root\.closeTransfer\(\).*"
    r"root\.changesService\.refresh\(\).*"
    r"root\.branchWorkspaceService\.refresh\(\)",
    "successful line transfer must close and refresh source/worktree state",
)

print("Git line transfer UI contracts: PASS")
